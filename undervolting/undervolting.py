import pycommons

import logging
from pycommons import generic_logging
generic_logging.init(level=logging.INFO)
logger = logging.getLogger(__file__)

import os,sys,argparse

import collections
import random
import time
import multiprocessing
import json
import signal
import math

import cpuprof
from cpuprof import adb


DEBUG = False

Level = collections.namedtuple('Level', 'CPU_KHz  PLL_L_Val   L2_KHz  VDD_Dig  VDD_Mem  BW_Mbps  VDD_Core  UA_Core  AVS')

def get_frequencies(device):
	ret, stdout, stderr = device.shell("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_frequencies")
	assert ret == 0, "Failed to get available frequencies: {}".format(stderr)
	frequencies = [int(x) for x in ' '.join(stdout.split()).split()]
	return frequencies

def set_level(device, frequency):
	ret, stdout, stderr = device.shell("echo {}>/sys/dvfs/level".format(frequency))
	assert ret == 0, "Failed to set level: {}".format(stderr)

def get_level(device):
	ret, stdout, stderr = device.shell("cat /sys/dvfs/vdd")
	assert ret == 0, "Failed to read vdd: {}".format(stderr)
	level = None
	try:
		level_str = stdout.strip().split("\n")[-1]
		level = Level(*[int(x) for x in level_str.split()])
	except Exception, e:
		logger.error("stdout: {}".format(stdout))
		logger.error("level_str: {}".format(level_str))
		raise e
	return level

def test_undervolt(device, level, vdd, frequencies):
	# First, disable all but 1 core
	ncpus = device.get_ncpus()
	assert ncpus != None, "#CPUs is None"

	for cpu in range(ncpus):
		device.set_core(cpu, 1)
	# Now set it to the lowest frequency that is != level.CPU_KHz
	device.shell("cpufreq set gov userspace")
	for f in frequencies:
		min_freq = f
		if min_freq != level.CPU_KHz:
			break
	device.shell("cpufreq set freq {}".format(min_freq))

	# Now, set voltage
	ret, stdout, stderr = device.shell("echo {}>/sys/dvfs/vdd".format(vdd))
	if ret != 0:
		raise Exception(stderr)

	result = True
	try:
		# Now, set it to the corresponding frequency
		device.shell("cpufreq set freq {}".format(level.CPU_KHz), wait_for_online=False)

		# Toggle screen to make sure it stays on
		device.toggle_screen(wait_for_online=False)
		if not device.is_screen_on(wait_for_online=False):
			device.toggle_screen(wait_for_online=False)

		# Now run workload
		# We iterate twice since, sometimes, the workload runs the first time and reboots once finished
		iterations = 2 if not DEBUG else 1
		device.shell("am broadcast -a MyGLRenderer.start", wait_for_online=False)
		for i in range(iterations):
			#ret, stdout, stderr = device.shell(r"cpupower -n 4 -f {} -c 4 -- pi 100000 0 0".format(level.CPU_KHz), wait_for_online=False)
			ret, stdout, stderr = device.shell(r'''cpu-stress -j {} -t 60'''.format(ncpus))
			if ret != 0:
				raise Exception("ret = {}: {}".format(ret, stderr))
			else:
				# Sometimes, workload returns despite reboot..not sure why
				if 'Finished:' not in stdout:
					raise Exception("Did not finish properly: stdout: {}".format(stdout))
			logger.info(stdout)
			time.sleep(1)
		device.shell("am broadcast -a MyGLRenderer.stop", wait_for_online=False)
		device.shell("cpufreq set freq {}".format(frequencies[0]))
	except Exception, e:
		logger.info("Failed! Phone probably rebooting..Got exception: {}".format(e))
		result = False
	finally:
		return result

def wait_for_device(device, sleep=45):
	logger.info("Waiting for device to finish reboot")
	time.sleep(sleep)
	device.wait_for_device_with_reset()
	logger.info("Device is back..")

def start_undervolting(device, frequencies, uv_frequencies, queue=None):
	signal.signal(signal.SIGINT, signal.SIG_IGN)
	err = None
	min_vdd = None
	try:
		# Go root
		device.root()
		time.sleep(1)

		for freq in uv_frequencies:
			try:
				# Get voltage under frequency
				# First, set level
				set_level(device, freq)

				# Now, read vdd
				level = get_level(device)
				if level.CPU_KHz != freq:
					raise Exception("Tried to set level '{}' but somehow ended up with '{}'".format(freq, level.CPU_KHz))
				max_vdd = level.VDD_Core
				min_vdd = max_vdd - 250000
				vdd_step = 5000 if not DEBUG else 140000
				vdd_range = range(min_vdd, max_vdd, vdd_step)
				vdd_range += [max_vdd]

				# Now we have a list over which we can do binary search
				# Now, start the binary search
				mx = len(vdd_range)
				mn = 0
				cur = None

				while mn <= mx:
					cur = (mx + mn) / 2
					cur_vdd = vdd_range[cur]

					if mx-mn <= 1:
						break

					approx_remaining_steps = math.log(mx - mn, 2)
					logger.info("{}: Testing: {}({})  (approx {} more steps)".format(device.deviceid, cur_vdd, cur, approx_remaining_steps))

					result = test_undervolt(device, level, cur_vdd, frequencies)
					if result is True:
						# This voltage was successful, lower the max
						mx = cur
						logger.info("{} - {}: Succeeded".format(device.deviceid, cur_vdd))
					else:
						# This voltage was unsuccessful, raise the min
						mn = cur
						# First, wait for device to come back online
						wait_for_device(device)
						# Now root since device has rebooted
						device.root()
						time.sleep(1)
						# Now, set the level
						set_level(device, freq)
						# Now loop back
				min_vdd = vdd_range[cur]
				logger.info("{} minimum vdd: {}".format(device.deviceid, vdd_range[cur]))
			except Exception, e:
				err = e
				logger.error("%s - \n%s\n" % (device, traceback.format_exc()))
				print err
			finally:
				if queue:
					queue.put((device.deviceid, min_vdd, freq, err))
				# Now reboot the device to reset state
				device.reboot()
				wait_for_device(device, 60)

	except Exception, e:
		err = e
		logger.error("%s - \n%s\n" % (device, traceback.format_exc()))
		print err
	finally:
		pass


def main(argv):
	devices = None
	offline = [[]]
	while True:
		devices, offline = adb.adb_devices(True)
		if len(offline) == 0:
			break
		for d in offline:
			adb.reset(d.deviceid)
		time.sleep(1)

	logger.info("Waiting for all devices to settle down")
	time.sleep(5)

	pool = pycommons.pool.NonDaemonPool()
	manager = multiprocessing.Manager()
	queue = manager.Queue()

	count = 0
	for device in devices:
		# Get all frequencies
		frequencies = get_frequencies(device)

		# Run everything for a set of frequencies
		uv_frequencies = [frequencies[0], frequencies[len(frequencies)/2], frequencies[-1]]
		#uv_frequencies = [frequencies[0], frequencies[-1]]
		uv_frequencies = [uv_frequencies[-2]]


		#pool.apply_async(func=start_undervolting, args=(device, frequencies, uv_frequencies, queue, ))
		start_undervolting(device, frequencies, uv_frequencies, queue)
		count += len(uv_frequencies)
	pool.close()

	idx = 0
	device_map = {}
	while idx < count:
		deviceid, min_vdd, freq, err = queue.get()
		if err:
			logger.error("{}".format(err))
		print 'Got data for freq: {}'.format(freq)

		device = None
		for d in devices:
			if d.deviceid == deviceid:
				device = d
				break

		if not device_map.get(deviceid, None):
			device_map[deviceid] = {
				'pvs_bin': device.get_pvs_bin(),
			}
		if err is not None:
			device_map[deviceid][freq]['error'] = str(err)
		device_map[deviceid][freq] = {
			'min_vdd': min_vdd
		}
		idx += 1
	pool.join()

	print json.dumps(device_map, indent=2)

if __name__ == '__main__':
	main(sys.argv)



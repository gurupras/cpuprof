import os,sys,argparse
import re
import subprocess
import time

from pycommons import generic_logging
import logging
logger = logging.getLogger('common')

import pycommons

class Device(object):

	def __init__(self, deviceid):
		self.deviceid = deviceid

	def run(self, args, wait_for_online=True):
		if wait_for_online:
			# First, make sure device is online before trying
			while True:
				ret, stdout, stderr = pycommons.run('''adb -s %s get-state''' % (self.deviceid), fail_on_error=False)
				if ret != 0 or stdout.strip() != 'device':
					reset(self.deviceid)
					time.sleep(3)
					continue
				time.sleep(0.3)
				break

		# Clear values
		ret = None
		stdout = None
		stderr = None

		for i in range(3):
			ret, stdout, stderr = pycommons.run('''adb -s %s %s''' % (self.deviceid, args), fail_on_error=False)
			if ret == 0:
				break
			time.sleep(1)
		time.sleep(0.3)
		if ret != 0:
			raise Exception(stderr)
		return ret, stdout, stderr

	def shell(self, cmd, *args, **kwargs):
#		pycommons.run('''adb -s %s "%s"''' % (self.deviceid, cmd))
		return self.run('shell "%s"' % (cmd), *args, **kwargs)

	def root(self):
#		pycommons.run('''adb -s %s root''' % (self.deviceid))
		self.wait_for_device_with_reset()
		ret, stdout, stderr = self.run('root')
		time.sleep(3)
		self.wait_for_device_with_reset()

	def wait_for_device(self, *args, **kwargs):
		return self.run('wait-for-device', *args, **kwargs)

	def wait_for_device_with_reset(self):
		while True:
			state = self.get_state()
			if state != 'device':
				logger.info("{} -> {}".format(self.deviceid, state))
				time.sleep(1)
				reset(self.deviceid)
			else:
				break

	def wait_for_boot_complete(self):
		while True:
			state = self.get_prop('sys.boot_completed')

	def get_codename(self):
		return self.get_prop('ro.hardware')

	def get_state(self, *args, **kwargs):
		ret = None
		stderr = None
		try:
			ret, stdout, stderr = self.run('get-state', *args, **kwargs)
			if ret != 0:
				raise Exception(stderr)
			return stdout.strip()
		except:
			raise Exception("{}->get_state() failed! :{}: {}".format(self.deviceid, ret, stderr))

	def get_prop(self, prop, *args, **kwargs):
		ret = None
		stderr = None
		try:
			ret, stdout, stderr = self.shell("getprop {}".format(prop), *args, **kwargs)
			if ret != 0:
				raise Exception(stderr)
			return stdout.strip()
		except:
			raise Exception("{}->get_prop({}) failed! :{}: {}".format(self.deviceid, prop, ret, stderr))

	def get_ncpus(self, *args, **kwargs):
		if getattr(self, 'ncpus', None) is None:
			ret = None
			stderr = None
			try:
				ret, stdout, stderr = self.shell("ls -d /sys/devices/system/cpu/cpu?", *args, **kwargs)
				if ret != 0:
					raise Exception(stderr)
				ncpus = len(stdout.strip().split())
				self.ncpus = ncpus
			except:
				raise Exception("{}->get_ncpus() failed! :{}: {}".format(self.deviceid, ret, stderr))
		return self.ncpus

	def get_governor(self, cpu, *args, **kwargs):
		ret = None
		stderr = None
		try:
			ret, stdout, stderr = self.shell('cat /sys/devices/system/cpu/cpu{}/cpufreq/scaling_governor'''.format(cpu), *args, **kwargs)
			if ret != 0:
				raise Exception(stderr)
			return stdout.strip()
		except:
			raise Exception("{}->get_prop({}) failed! :{}: {}".format(self.deviceid, prop, ret, stderr))


	def get_frequency(self, cpu, *args, **kwargs):
		ret = None
		stderr = None
		try:
			ret, stdout, stderr = self.shell('cat /sys/devices/system/cpu/cpu{}/cpufreq/scaling_cur_freq'''.format(cpu), *args, **kwargs)
			if ret != 0:
				raise Exception(stderr)
			return int(stdout.strip())
		except:
			raise Exception("{}->get_frequency({}) failed! :{}: {}".format(self.deviceid, cpu, ret, stderr))

	def set_governor(self, cpu, governor, *args, **kwargs):
		ret = None
		stderr = None
		try:
			ret, stdout, stderr = self.shell('''echo {}>/sys/devices/system/cpu/cpu{}/cpufreq/scaling_governor'''.format(governor, cpu), *args, **kwargs)
			if ret != 0:
				raise Exception(stderr)
		except:
			raise Exception("{}->set_governor({}, {}) failed! :{}: {}".format(self.deviceid, cpu, governor, ret, stderr))
		return ret, stdout, stderr


	def set_frequency(self, cpu, speed, *args, **kwargs):
		ret = None
		stderr = None
		try:
			ret, stdout, stderr = self.shell('''echo {}>/sys/devices/system/cpu/cpu{}/cpufreq/scaling_setspeed'''.format(speed, cpu), *args, **kwargs)
			if ret != 0:
				raise Exception(stderr)
		except:
			raise Exception("{}->set_frequency({}, {}) failed! :{}: {}".format(self.deviceid, cpu, speed, ret, stderr))
		return ret, stdout, stderr


	def set_core(self, cpu, state, *args, **kwargs):
		ret = None
		stderr = None
		try:
			ret, stdout, stderr = self.shell('''echo {}>/sys/devices/system/cpu/cpu{}/online'''.format(state, cpu), *args, **kwargs)
			if ret != 0:
				raise Exception(stderr)
		except:
			raise Exception("{}->set_core({}, {}) failed! :{}: {}".format(self.deviceid, cpu, state, ret, stderr))
		return ret, stdout, stderr


	def toggle_screen(self, *args, **kwargs):
		ret = None
		stderr = None
		try:
			ret, stdout, stderr = self.shell('''input keyevent 26''', *args, **kwargs)
			if ret != 0:
				raise Exception(stderr)
		except:
			raise Exception("{}->toggle_screen() failed! :{}: {}".format(self.deviceid, ret, stderr))
		return ret, stdout, stderr


	def is_screen_on(self, *args, **kwargs):
		ret = None
		stderr = None
		fg_pid = -1
		try:
			ret, stdout, stderr = self.shell(r'''dumpsys input_method | grep mInteractive''', *args, **kwargs)
			if ret != 0:
				raise Exception(stderr)
			if 'mInteractive=true' in stdout:
				return True
			else:
				return False
		except:
			raise Exception("{}->is_screen_on() failed! :{}: {}".format(self.deviceid, ret, stderr))


	def get_pvs_bin(self, *args, **kwargs):
		pvs_bin = -1
		files = [
			"/sys/module/clock_krait_8974/parameters/table_name",
			"/sys/kernel/debug/acpuclk/pvs_bin",
		]
		if getattr(self, 'pvs_bin', None) is None:
			for file in files:
				ret, stdout, stderr = self.shell("cat {}".format(file), *args, **kwargs)
				if ret == 0 and len(stdout) < 30:	#FIXME: Hard-coded rule
					pvs_bin = stdout.strip()
					self.pvs_bin = pvs_bin
				else:
					logger.error("Failed to read pvs_bin: \n{}\n".format(stderr))
		return pvs_bin

	def reboot(self, *args, **kwargs):
		self.shell('reboot', *args, **kwargs)

	def __str__(self):
		return self.deviceid

	def __repr__(self):
		return self.deviceid


def reset(deviceid=None):
	cmdline = './usbreset'
	if deviceid is not None:
		cmdline += ' --device-id {}'.format(deviceid)
	else:
		cmdline += ' --name Goog'

	while True:
		ret, stdout, stderr = pycommons.run(cmdline, fail_on_error=False)
		if ret == 0:
			break
		time.sleep(1)
	time.sleep(5)

def adb_devices(include_offline=False, include_other=False):
	online = []
	offline = []
	other = []
	pattern = re.compile(r'''(?P<id>[a-zA-Z0-9]+)\s+(?P<state>(device|offline|bootloader))''')
	p = subprocess.Popen('adb devices', shell=True, stdout=subprocess.PIPE,
			stderr=subprocess.PIPE)
	p.wait()

	stdout, stderr = p.communicate()

	if len(stderr) != 0:
		print stderr

	strings = stdout.split('\n')
	for line in strings:
		line = line.strip()
		m = pattern.match(line)
		if not m:
			logger.debug('Did not match pattern: ' + line)
			continue
		m = m.groupdict()
		list = None
		if m['state'] == 'offline':
			list = offline
		elif m['state'] == 'device':
			list = online
		else:
			list = other
		list.append(Device(m['id']))
	result = [online]
	if include_offline:
		result.append(offline)
	if include_other:
		result.append(other)
	return result


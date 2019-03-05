import os,sys,argparse,re
import json
import logging
import datetime

from collections import namedtuple

import parse_logcat

TRACE_STRING = r'\s*(?P<thread>.*?)\s+\[(?P<cpu>\d+)\]\s+(?P<unknown>.{4})\s+(?P<timestamp>\d+\.\d+): (?P<message>(?P<tag>.*?):\s+(?P<text>.*))'
TRACE_PATTERN = re.compile(TRACE_STRING)
Trace = namedtuple("Trace", ['thread', 'cpu', 'unknown', 'timestamp', 'tag', 'trace_token', 'datetime'])

LOGCAT_TRACE_PAYLOAD_STR = r'\s*(?P<thread>.*?)\s+\[(?P<cpu>\d+)\]\s+(?P<unknown>.{4})\s+(?P<timestamp>\d+\.\d+):\s*((?P<trace_token>\d+)\s*)?(?P<message>(?P<tag>.*?):\s+(?P<text>.*))'
LOGCAT_TRACE_PAYLOAD_PATTERN = re.compile(LOGCAT_TRACE_PAYLOAD_STR)

def test():
	m = TRACE_PATTERN.match('      mpdecision-2951  [000] ...1   961.972863: sched_cpu_hotplug: cpu 1 online error=0')
	print m.groupdict()

''' Format: cpu 1 offline error=0 '''
SCHED_CPU_HOTPLUG_PATTERN = re.compile(r'\s*cpu\s+(?P<cpu>\d+)\s+(?P<state>[a-zA-Z0-9_]+)\s+error=(?P<error>-?\d+)')
SchedCpuHotplug = namedtuple("SchedCpuHotplug", ['cpu', 'state', 'error'])
_SchedCpuHotplug = namedtuple("_SchedCpuHotplug", Trace._fields + ('sched_cpu_hotplug',))
def sched_cpu_hotplug(text, result):
	tag = result['tag']
	common_text_parse(text, tag, SCHED_CPU_HOTPLUG_PATTERN, result)
	result[tag]['cpu'] = int(result[tag]['cpu'])
	result[tag]['error'] = int(result[tag]['error'])

	result[tag] = SchedCpuHotplug(**result[tag])
	return _SchedCpuHotplug(**result)

''' Format: sensor_id=5 temp=59 '''
THERMAL_TEMP_PATTERN = re.compile(r'\s*sensor_id=(?P<sensor_id>\d+)\s+temp=(?P<temp>\d+).*')
ThermalTemp = namedtuple("ThermalTemp", ['sensor_id', 'temp'])
_ThermalTemp = namedtuple("_ThermalTemp", Trace._fields + ('thermal_temp',))
def thermal_temp(text, result):
	tag = result['tag']
	common_text_parse(text, tag, THERMAL_TEMP_PATTERN, result)
	result[tag]['sensor_id'] = int(result[tag]['sensor_id'])
	result[tag]['temp'] = int(result[tag]['temp'])

	result[tag] = ThermalTemp(**result[tag])
	return _ThermalTemp(**result)

''' Format: temp=53 '''
TEMPFREQ_TEMP_PATTERN = re.compile(r'\s*temp=(?P<temp>\d+).*')
TempfreqTemp = namedtuple("TempfreqTemp", ['temp'])
_TempfreqTemp = namedtuple("_TempfreqTemp", Trace._fields + ('tempfreq_temp',))
def tempfreq_temp(text, result):
	tag = result['tag']
	common_text_parse(text, tag, TEMPFREQ_TEMP_PATTERN, result)
	result[tag]['temp'] = int(result[tag]['temp'])

	result[tag] = TempfreqTemp(**result[tag])
	return _TempfreqTemp(**result)

''' Format: cpu_frequency: state=2265600 cpu_id=0 '''
CPU_FREQUENCY_PATTERN = re.compile(r'\s*state=(?P<state>\d+)\s+cpu_id=(?P<cpu_id>\d+)')
CpuFrequency = namedtuple("CpuFrequency", ['cpu_id', 'state'])
_CpuFrequency = namedtuple("_CpuFrequency", Trace._fields + ('cpu_frequency',))
def cpu_frequency(text, result):
	tag = result['tag']
	common_text_parse(text, tag, CPU_FREQUENCY_PATTERN, result)
	result[tag]['cpu_id'] = int(result[tag]['cpu_id'])
	result[tag]['state'] = int(result[tag]['state'])

	result[tag] = CpuFrequency(**result[tag])
	return _CpuFrequency(**result)

''' Format: cpu_frequency_switch_start: start=422400 end=300000 cpu_id=0 '''
CPU_FREQUENCY_SWITCH_START_PATTERN = re.compile(r'\s*start=(?P<start>\d+) end=(?P<end>\d+) cpu_id=(?P<cpu_id>\d+)')
CpuFrequencySwitchStart = namedtuple("CpuFrequencySwitchStart", ['start', 'end', 'cpu_id'])
_CpuFrequencySwitchStart = namedtuple("_CpuFrequencySwitchStart", Trace._fields + ('cpu_frequency_switch_start',))
def cpu_frequency_switch_start(text, result):
	tag = result['tag']
	common_text_parse(text, tag, CPU_FREQUENCY_SWITCH_START_PATTERN, result)
	# Everything is integer
	for key in result[tag].keys():
		result[tag][key] = int(result[tag][key])

	result[tag] = CpuFrequencySwitchStart(**result[tag])
	return _CpuFrequencySwitchStart(**result)

''' Format: cpu_frequency_switch_end: cpu_id=0 '''
CPU_FREQUENCY_SWITCH_END_PATTERN = re.compile(r'\s*cpu_id=(?P<cpu_id>\d+)')
CpuFrequencySwitchEnd = namedtuple("CpuFrequencySwitchEnd", ['cpu_id'])
_CpuFrequencySwitchEnd = namedtuple("_CpuFrequencySwitchEnd", Trace._fields + ('cpu_frequency_switch_end',))
def cpu_frequency_switch_end(text, result):
	tag = result['tag']
	common_text_parse(text, tag, CPU_FREQUENCY_SWITCH_END_PATTERN, result)
	result[tag]['cpu_id'] = int(result[tag]['cpu_id'])

	result[tag] = CpuFrequencySwitchEnd(**result[tag])
	return _CpuFrequencySwitchEnd(**result)

''' Format: kgsl_gpubusy: d_name=kgsl-3d0 busy=489602 elapsed=1000411 '''
KGSL_GPUBUSY_PATTERN = re.compile(r'\s*d_name=(?P<d_name>.*?)\s+busy=(?P<busy>\d+)\s+elapsed=(?P<elapsed>\d+)')
KgslGpuBusy = namedtuple("KgslGpuBusy", ['d_name', 'busy', 'elapsed'])
_KgslGpuBusy = namedtuple("_KgslGpuBusy", Trace._fields + ('kgsl_gpubusy',))
def kgsl_gpubusy(text, result):
	tag = result['tag']
	common_text_parse(text, tag, KGSL_GPUBUSY_PATTERN, result)
	result[tag]['busy'] = int(result[tag]['busy'])
	result[tag]['elapsed'] = int(result[tag]['elapsed'])

	result[tag] = KgslGpuBusy(**result[tag])
	return _KgslGpuBusy(**result)

''' Format: kgsl_pwrlevel: d_name=kgsl-3d0 pwrlevel=4 freq=320000000 '''
KGSL_PWR_LEVEL_PATTERN = re.compile(r'\s*d_name=(?P<d_name>.*?)\s+pwrlevel=(?P<pwrlevel>\d+)\s+freq=(?P<freq>\d+)')
KgslPwrLevel = namedtuple("KgslPwrLevel", ['d_name', 'pwr_level', 'freq'])
_KgslPwrLevel = namedtuple("_KgslPwrLevel", Trace._fields + ('kgsl_pwrlevel',))
def kgsl_pwrlevel(text, result):
	tag = result['tag']
	common_text_parse(text, tag, KGSL_PWR_LEVEL_PATTERN, result)
	result[tag]['pwrlevel'] = int(result[tag]['pwrlevel'])
	result[tag]['freq'] = int(result[tag]['freq'])

	result[tag] = KgslPwrLevel(**result[tag])
	return _KgslPwrLevel(**result)

''' Format: phonelab_num_online_cpus: num_online_cpus=4 '''
PHONELAB_NUM_ONLINE_CPUS_PATTERN = re.compile(r'\s*num_online_cpus=(?P<num_online_cpus>\d+)')
PhonelabNumOnlineCpus = namedtuple("PhonelabNumOnlineCpus", ['num_online_cpus'])
_PhonelabNumOnlineCpus = namedtuple("_PhonelabNumOnlineCpus", Trace._fields + ('phonelab_num_online_cpus',))
def phonelab_num_online_cpus(text, result):
	tag = result['tag']
	common_text_parse(text, tag, PHONELAB_NUM_ONLINE_CPUS_PATTERN, result)
	result[tag]['num_online_cpus'] = int(result[tag]['num_online_cpus'])

	result[tag] = PhonelabNumOnlineCpus(**result[tag])
	return _PhonelabNumOnlineCpus(**result)

def phonelab_periodic_ctx_switch_info(text, result):
	return phonelab_periodic_ctx_switch_info_hash(text, result)

''' Format: phonelab_periodic_ctx_switch_info: cpu=2 pid=157 tgid=157 comm=kworker/2:0H utime_t=3 stime_t=0 utime=0 stime=0 cutime_t=0 cstime_t=0 cutime=0 cstime=0 log_idx=1'''
PHONELAB_PERIODIC_CTX_SWITCH_INFO_ORIG_PATTERN = re.compile(r'\s*cpu=(?P<cpu>\d+) pid=(?P<pid>\d+) tgid=(?P<tgid>\d+) comm=(?P<comm>.*?) utime_t=(?P<utime_t>\d+) stime_t=(?P<stime_t>\d+) ' + \
		'utime=(?P<utime>\d+) stime=(?P<stime>\d+) cutime_t=(?P<cutime_t>\d+) cstime_t=(?P<cstime_t>\d+) cutime=(?P<cutime>\d+) cstime=(?P<cstime>\d+) log_idx=(?P<log_idx>\d+)')
PhonelabPeriodicCtxSwitchInfoOrig = namedtuple("PeriodicCtxSwitchInfo", ['cpu', 'tgid', 'comm', 'utime_t', 'stime_t', 'utime', 'stime', 'cutime_t', 'cstime_t', 'cutime', 'cstime', 'log_idx'])
_PhonelabPeriodicCtxSwitchInfoOrig = namedtuple("_PhonelabPeriodicCtxSwitchInfoOrig", Trace._fields + ('phonelab_periodic_ctx_switch_info',))
def phonelab_periodic_ctx_switch_info_orig(text, result):
	import ipdb; ipdb.set_trace()
	tag = result['tag']
	common_text_parse(text, tag, PHONELAB_PERIODIC_CTX_SWITCH_INFO_ORIG_PATTERN, result)
	# Everything is integer except comm
	keys = list(result[tag].keys())
	keys.remove('comm')
	for key in keys:
		result[tag][key] = int(result[tag][key])

	result[tag] = PhonelabPeriodicCtxSwitchInfoOrig(**result[tag])
	return _PhonelabPeriodicCtxSwitchInfoOrig(**result)

''' Format: phonelab_periodic_ctx_switch_info: cpu=1 pid=7641 tgid=7613 nice=0 comm=Binder_1 utime=0 stime=0 rtime=158906 bg_utime=0 bg_stime=0 bg_rtime=0 s_run=0 s_int=2 s_unint=0 s_oth=0 log_idx=79981'''
PHONELAB_PERIODIC_CTX_SWITCH_INFO_HASH_PATTERN= re.compile(r'\s*cpu=(?P<cpu>\d+) pid=(?P<pid>\d+) tgid=(?P<tgid>\d+) nice=(?P<nice>-?\d+) comm=(?P<comm>.*?) utime=(?P<utime>\d+) stime=(?P<stime>\d+) ' + \
		'rtime=(?P<rtime>\d+) bg_utime=(?P<bg_utime>\d+) bg_stime=(?P<bg_stime>\d+) bg_rtime=(?P<bg_rtime>\d+) s_run=(?P<s_run>\d+) s_int=(?P<s_int>\d+) s_unint=(?P<s_unint>\d+) s_oth=(?P<s_oth>\d+) log_idx=(?P<log_idx>\d+)')
PeriodicCtxSwitchInfo = namedtuple("PeriodicCtxSwitchInfo", ['cpu', 'pid', 'tgid', 'nice', 'comm', 'utime', 'stime', 'rtime', 'bg_utime', 'bg_stime', 'bg_rtime', 's_run', 's_int', 's_unint', 's_oth', 'log_idx'])
_PeriodicCtxSwitchInfo = namedtuple("_PeriodicCtxSwitchInfo", Trace._fields + ('phonelab_periodic_ctx_switch_info',))
def phonelab_periodic_ctx_switch_info_hash(text, result):
	tag = result['tag']
	common_text_parse(text, tag, PHONELAB_PERIODIC_CTX_SWITCH_INFO_HASH_PATTERN, result)
	# Everything is integer except comm
	keys = list(result[tag].keys())
	keys.remove('comm')
	for key in keys:
		result[tag][key] = int(result[tag][key])
	result[tag] = PeriodicCtxSwitchInfo(**result[tag])
	return _PeriodicCtxSwitchInfo(**result)

''' Format: phonelab_periodic_ctx_switch_marker: BEGIN cpu=0 count=0 log_idx=892'''
'''	Format: phonelab_periodic_ctx_switch_marker: END cpu=0 count=19 log_idx=892 '''
PHONELAB_PERIODIC_CTX_SWITCH_MARKER_PATTERN = re.compile(r'\s*(?P<type>BEGIN|END)\s*cpu=(?P<cpu>\d+)\s*count=(?P<count>\d+)\s*log_idx=(?P<log_idx>\d+)')
PhonelabPeriodicCtxSwitchMarker = namedtuple("PhonelabPeriodicCtxSwitchMarker", ['type', 'cpu', 'count', 'log_idx'])
_PhonelabPeriodicCtxSwitchMarker = namedtuple("_PhonelabPeriodicCtxSwitchMarker", Trace._fields + ('phonelab_periodic_ctx_switch_marker',))
def phonelab_periodic_ctx_switch_marker(text, result):
	tag = result['tag']
	common_text_parse(text, tag, PHONELAB_PERIODIC_CTX_SWITCH_MARKER_PATTERN, result)
	result[tag]['cpu'] = int(result[tag]['cpu'])
	result[tag]['count'] = int(result[tag]['count'])
	result[tag]['log_idx'] = int(result[tag]['log_idx'])

	result[tag] = PhonelabPeriodicCtxSwitchMarker(**result[tag])
	return _PhonelabPeriodicCtxSwitchMarker(**result)

''' Format: phonelab_periodic_warning_cpu: warning=destroy_periodic_work cpu=2 '''
PHONELAB_PERIODIC_WARNING_CPU_PATTERN = re.compile(r'\s*warning=(?P<message>.*)? cpu=(?P<warning_cpu>\d+)\s*')
PhonelabPeriodicWarningCpu = namedtuple("PhonelabPeriodicWarningCpu", ['warning', 'warning_cpu'])
_PhonelabPeriodicWarningCpu = namedtuple("_PhonelabPeriodicWarningCpu", Trace._fields + ('phonelab_periodic_warning_cpu',))
def phonelab_periodic_warning_cpu(text, result):
	tag = result['tag']
	common_text_parse(text, tag, PHONELAB_PERIODIC_WARNING_CPU_PATTERN, result)

	result[tag]['warning_cpu'] = int(result[tag]['warning_cpu'])

#	result[tag] = PhonelabPeriodicWarningCpu(**result[tag])
	return _PhonelabPeriodicWarningCpu(**result)
	result[tag] = None

''' Format: phonelab_timing: func=periodic_ctx_switch_info time=33334ns cpu=0 '''
PHONELAB_TIMING_PATTERN = re.compile(r'\s*func=(?P<func>.*?) time=(?P<time>\d+)ns cpu=(?P<cpu>\d+)')
PhonelabTiming = namedtuple("PhonelabTiming", ['func', 'time', 'cpu'])
_PhonelabTiming = namedtuple("_PhonelabTiming", Trace._fields + ('phonelab_timing',))
def phonelab_timing(text, result):
	tag = result['tag']
	common_text_parse(text, tag, PHONELAB_TIMING_PATTERN, result)
	result[tag]['cpu'] = int(result[tag]['cpu'])
	result[tag]['time'] = int(result[tag]['time'])

#	result[tag] = PhonelabTiming(**result[tag])
	return _PhonelabTiming(**result)

	result[tag] = None

''' Format: phonelab_proc_foreground: pid=11786 tgid=11786 comm=.apps.messaging '''
PHONELAB_PROC_FOREGROUND_PATTERN = re.compile(r'\s*pid=(?P<pid>\d+) tgid=(?P<tgid>\d+) comm=(?P<comm>.*)')
PhonelabProcForeground = namedtuple("PhonelabProcForeground", ['pid', 'tgid', 'comm'])
_PhonelabProcForeground = namedtuple("_PhonelabProcForeground", Trace._fields + ('phonelab_proc_foreground',))
def phonelab_proc_foreground(text, result):
	tag = result['tag']
	common_text_parse(text, tag, PHONELAB_PROC_FOREGROUND_PATTERN, result)
	result[tag]['pid'] = int(result[tag]['pid'])
	result[tag]['tgid'] = int(result[tag]['tgid'])

	result[tag] = PhonelabProcForeground(**result[tag])
	return _PhonelabProcForeground(**result)

''' Format: cpufreq_scaling: min=300000 max=2265600 cpu=0 '''
CPUFREQ_SCALING_PATTERN = re.compile(r'\s*min=(?P<min>\d+)\s+max=(?P<max>\d+)\s+cpu=(?P<scaling_cpu>\d+)\s*')
CpufreqScalingPattern = namedtuple("CpufreqScalingPattern", ['min', 'max', 'cpu'])
_CpufreqScalingPattern = namedtuple("_CpufreqScalingPattern", Trace._fields + ('cpufreq_scaling',))
def cpufreq_scaling(text, result):
	tag = result['tag']
	common_text_parse(text, tag, CPUFREQ_SCALING_PATTERN, result)
	result[tag]['min'] = int(result[tag]['min'])
	result[tag]['max'] = int(result[tag]['max'])
	result[tag]['scaling_cpu'] = int(result[tag]['scaling_cpu'])

	result[tag] = CpufreqScalingPattern(**result[tag])
	return _CpufreqScalingPattern(**result)

TRACING_MARK_WRITE_PATTERN = re.compile(r'\s*(?P<payload>.*)')
TracingMarkWrite = namedtuple("TracingMarkWrite", ['payload'])
_TracingMarkWrite = namedtuple("_TracingMarkWrite", Trace._fields + ('tracing_mark_write',))
def tracing_mark_write(text, result):
	tag = result['tag']
	common_text_parse(text, tag, TRACING_MARK_WRITE_PATTERN, result)
	result[tag] = TracingMarkWrite(**result[tag])
	return _TracingMarkWrite(**result)

''' Format plsc_open: {"action":"open", "start":347288430643, "delta":39323, "uid":0, "task":"thermal-engine-", "path":"/sys/devices/virtual/thermal/thermal_zone7/trip_point_1_temp", "pid":2784, "upid":836, "retval":15, "session":829, "size":4096, "type": 32768, "flags":131072, "mode":0} '''
PLSC_OPEN_PATTERN = re.compile(r'(?P<data>{"action":.*})')
PlscOpen = namedtuple("PlscOpen", ["action", "start", "delta", "uid", "task", "path", "pid", "upid", "retval", "session", "size", "type", "flags", "mode"])
_PlscOpen = namedtuple("_PlscOpen", Trace._fields + ('plsc_open',))
def plsc_common(text, result, PATTERN):
	tag = result['tag']
	common_text_parse(text, tag, PATTERN, result)
	data = json.loads(result[tag]['data'])
	return data

def plsc_open(text, result):
	tag = result['tag']
	data = plsc_common(text, result, PLSC_OPEN_PATTERN)
	result[tag] = PlscOpen(**data)
	return _PlscOpen(**result)

''' Format plsc_rw: {"action":"writev", "start":3453737812, "delta":4427, "pid":203, "upid":203, "retval":59, "session":90, "fd":4, "bytes":0, "offset":0} '''
PLSC_RW_PATTERN = re.compile(r'(?P<data>{"action":.*})')
PlscRw = namedtuple("PlscRw", ["action", "start", "delta", "pid", "upid", "retval", "session", "fd", "bytes", "offset"])
_PlscRw = namedtuple("_PlscRw", Trace._fields + ('plsc_rw',))
def plsc_rw(text, result):
	tag = result['tag']
	data = plsc_common(text, result, PLSC_RW_PATTERN)
	result[tag] = PlscRw(**data)
	return _PlscRw(**result)

def common_text_parse(text, tag, pattern, result):
	m = pattern.match(text)
	assert m, text
	d = m.groupdict()
	result[tag] = dict(d)
	result['timestamp'] = float(result['timestamp'])
	result['cpu'] = int(result['cpu'])

	# FIXME: Hack for missing trace token
	result['trace_token'] = result.get('trace_token', None) or 0

	# Clear up some unnecessary fields
	del result['text']
	del result['message']
#	del result['unknown']

def setup_parser(parser=None):
	if not parser:
		parser = argparse.ArgumentParser()
	parser.add_argument('file', type=str, help='File to parse')
	return parser

# -----------------------------------------------------------------
#  None of these functions are expected to be called directly!!!
#  Always use parse_logcat to parse loglines of all types
# -----------------------------------------------------------------
def process_line(line, logcat_info=None, pattern=LOGCAT_TRACE_PAYLOAD_PATTERN):
	m = pattern.match(line)
	if m:
		result = m.groupdict()
		if logcat_info:
			# Add any logcat fields that you need into the trace object here
			result['datetime'] = datetime.datetime.strptime(logcat_info['datetime'], "%Y-%m-%d %H:%M:%S.%f")
		else:
			result['datetime'] = datetime.datetime.now()
		tag = result['tag']
		try:
			func = globals()[tag]
			result = func(result['text'], result)
			return result
		except:
			pass
	return None

def process(file):
	traces = []
	with open(file, 'rb') as f:
		for line in f:
			if line[0] == '#':
				continue
			result = process_line(line)
			if result:
				traces.append(result)
			else:
				print "Line was not parsed: \n%s\n" % line
	return traces

def main(argv):
	parser = setup_parser()
	args = parser.parse_args(argv[1:])

	file = args.file
	traces = parse_logcat.process_trace(file)
	import pdb
	pdb.set_trace()

if __name__ == '__main__':
	main(sys.argv)

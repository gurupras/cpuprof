package cpuprof_test

import (
	"testing"

	"github.com/gurupras/cpuprof"
)

func TestCheckLogcatPattern(t *testing.T) {
	var success bool = true
	result := cpuprof.InitResult("TestCheckLogcatPattern")

	line := "6b793913-7cd9-477a-bbfa-62f07fbac87b 2016-04-21 09:59:01.199025638 11553177 [29981.752359]   202   202 D Kernel-Trace:      kworker/1:1-21588 [001] ...2 29981.751893: phonelab_periodic_ctx_switch_info: cpu=1 pid=7641 tgid=7613 nice=0 comm=Binder_1 utime=0 stime=0 rtime=158906 bg_utime=0 bg_stime=0 bg_rtime=0 s_run=0 s_int=2 s_unint=0 s_oth=0 log_idx=79981"

	logline := cpuprof.ParseLogline(line)
	if logline == nil {
		success = false
	}

	//	fmt.Println(logline)

	cpuprof.HandleResult(t, success, result)
}

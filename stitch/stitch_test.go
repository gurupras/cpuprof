package main

import (
	"testing"

	"github.com/google/shlex"
	"github.com/gurupras/cpuprof"
)

func TestStitch(t *testing.T) {
	var success bool = false
	var err error

	result := cpuprof.InitResult("TestStitch")
	cmdline, err := shlex.Split("stitch_test.go /android/test-cpuprof/1b0676e5fb2d7ab82a2b76887c53e94cf0410826 --regex *.out.gz -j 4")
	cpuprof.StitchMain(cmdline)
	if err == nil {
		success = true
	}

	cpuprof.HandleResult(t, success, result)
}

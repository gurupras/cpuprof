package cpuprof

import (
	"errors"
	"fmt"
	"reflect"
	"regexp"
	"strconv"
	"time"

	"github.com/gurupras/gocommons"
	"github.com/pbnjay/strptime"
)

var PATTERN = regexp.MustCompile(`` +
	`\s*(?P<line>` +
	`\s*(?P<boot_id>[a-z0-9\-]{36})` +
	`\s*(?P<datetime>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)` +
	`\s*(?P<LogcatToken>\d+)` +
	`\s*\[\s*(?P<tracetime>\d+\.\d+)\]` +
	`\s*(?P<pid>\d+)` +
	`\s*(?P<tid>\d+)` +
	`\s*(?P<level>[A-Z]+)` +
	`\s*(?P<tag>.*?):` +
	`\s*(?P<payload>.*)` +
	`)`)
var PHONELAB_PATTERN = regexp.MustCompile(`` +
	`\s*(?P<line>` +
	`(?P<deviceid>[a-z0-9]+)` +
	`\s*(?P<logcat_timestamp>\d+)` +
	`\s*(?P<logcat_timestamp_sub>\d+(\.\d+)?)` +
	`\s*(?P<boot_id>[a-z0-9\-]{36})` +
	`\s*(?P<LogcatToken>\d+)` +
	`\s*(?P<tracetime>\d+\.\d+)` +
	`\s*(?P<datetime>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)` +
	`\s*(?P<pid>\d+)` +
	`\s*(?P<tid>\d+)` +
	`\s*(?P<level>[A-Z]+)` +
	`\s*(?P<tag>.*?)` +
	`\s*(?P<payload>.*)` +
	`)`)

func ParseLogline(line string) *Logline {
	var err error

	names := PHONELAB_PATTERN.SubexpNames()
	values_raw := PHONELAB_PATTERN.FindAllStringSubmatch(line, -1)
	if values_raw == nil {
		names = PATTERN.SubexpNames()
		values_raw = PATTERN.FindAllStringSubmatch(line, -1)
		if values_raw == nil {
			return nil
		}
	}
	values := values_raw[0]

	kv_map := map[string]string{}
	for i, value := range values {
		kv_map[names[i]] = value
	}

	// Convert values
	// Some datetimes are 9 digits instead of 6
	// TODO: Get rid of the last 3
	if len(kv_map["datetime"]) != 26 {
		kv_map["datetime"] = kv_map["datetime"][:26]
	}

	datetime, err := strptime.Parse(kv_map["datetime"], "%Y-%m-%d %H:%M:%S.%f")
	if err != nil {
		return nil
	}
	LogcatToken, err := strconv.ParseInt(kv_map["LogcatToken"], 0, 64)
	if err != nil {
		return nil
	}
	tracetime, err := strconv.ParseFloat(kv_map["tracetime"], 64)
	if err != nil {
		return nil
	}
	pid, err := strconv.ParseInt(kv_map["pid"], 0, 32)
	if err != nil {
		return nil
	}
	tid, err := strconv.ParseInt(kv_map["tid"], 0, 32)
	if err != nil {
		return nil
	}

	result := Logline{line, kv_map["boot_id"], datetime, LogcatToken,
		tracetime, int32(pid), int32(tid), kv_map["level"],
		kv_map["tag"], kv_map["payload"]}
	return &result
}

type Logline struct {
	Line        string
	BootId      string
	Datetime    time.Time
	LogcatToken int64
	TraceTime   float64
	Pid         int32
	Tid         int32
	Level       string
	Tag         string
	Payload     string
}

type Loglines []*Logline

func ParseLoglineConvert(line string) gocommons.SortInterface {
	return ParseLogline(line)
}

var (
	LoglineSortParams = gocommons.SortParams{LineConvert: ParseLoglineConvert, Lines: make(gocommons.SortCollection, 0)}
)

func (l *Logline) String() string {
	return l.Line
	//	return fmt.Sprintf("%v %v %v [%v] %v %v %v %v: %v",
	//		l.boot_id, l.datetime, l.LogcatToken, l.tracetime,
	//		l.pid, l.tid, l.level, l.tag, l.payload)
}

func (l *Logline) Less(s gocommons.SortInterface) (ret bool, err error) {
	var o *Logline
	var ok bool
	if s != nil {
		if o, ok = s.(*Logline); !ok {
			err = errors.New(fmt.Sprintf("Failed to convert from SortInterface to *Logline:", reflect.TypeOf(s)))
			ret = false
			goto out
		}
	}
	if l != nil && o != nil {
		if l.LogcatToken == o.LogcatToken {
			ret = l.Datetime.Before(o.Datetime)
		} else {
			ret = l.LogcatToken < o.LogcatToken
		}
	} else if l != nil {
		ret = true
	} else {
		ret = false
	}
out:
	return
}

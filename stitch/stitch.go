package main

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"sync"

	"github.com/alecthomas/kingpin"
	"github.com/gurupras/cpuprof"
	"github.com/gurupras/gocommons"
)

var (
	kpin    = kingpin.New("stitch", "")
	path    = kpin.Arg("path", "").Required().String()
	regex   = kpin.Flag("regex", "").Short('r').Default("*").String()
	j       = kpin.Flag("nthreads", "nthreads").Short('j').Default("32").Int()
	bufsize = kpin.Flag("bufsize", "Buffer size per thread").Short('b').Default("134217728").Int()
)

func Process(path string, regex string, nthreads int, bufsize int) error {
	files, _ := gocommons.ListFiles(path, regex)
	var overall_chunks []string
	var err error
	chunk_chan := make(chan []string)

	ext_sort := func(file string) {
		var chunks []string
		if chunks, err = gocommons.ExternalSort(file, nthreads, bufsize, false, cpuprof.LoglineSortParams); err != nil {
			return
		}
		chunk_chan <- chunks
	}

	for _, file := range files {
		go ext_sort(file)
	}
	// Wait for them to complete
	for i := 0; i < len(files); i++ {
		chunk := <-chunk_chan
		overall_chunks = append(overall_chunks, chunk...)
	}

	sort.Sort(sort.StringSlice(overall_chunks))
	/*
		output_file := filepath.Join(path, "sorted.gz")
		fmt.Printf("Merging chunks back into '%s'\n", output_file)
		err = gocommons.NWayMerge(overall_chunks, output_file, bufsize, cpuprof.LoglineSortParams)

		fmt.Printf("Removing chunks ...")
		for _, chunk := range overall_chunks {
			os.Remove(chunk)
		}
		fmt.Printf("Done\n")
	*/
	// Split by boot-id
	BootIdSplit(path, overall_chunks, 1000000)

	return nil
}

func BootIdSplit(path string, files []string, lines_per_file int) {
	var err error

	var infile_raw *gocommons.File
	var reader *bufio.Scanner
	bootid_channel_map := make(map[string]chan string, 0)
	var wg sync.WaitGroup

	boot_id_consumer := func(boot_id string, channel chan string) {
		wg.Add(1)
		defer wg.Done()

		cur_idx := 0
		cur_line_count := 0
		outdir := filepath.Join(path, boot_id)
		var cur_filename string
		var cur_file *gocommons.File
		var cur_file_writer gocommons.Writer

		// Make directory if it doesn't exist
		if _, err := os.Stat(outdir); os.IsExist(err) {
			// Does exit
			fmt.Println("Attempting to delete existing directory:", outdir)
			os.RemoveAll(outdir)
		}
		fmt.Println("Attempting to create directory:", outdir)
		if err = os.MkdirAll(outdir, 0775); err != nil {
			fmt.Fprintln(os.Stderr, "Failed to create directory:", outdir)
		}

		for {
			if cur_line_count == 0 {
				if cur_idx > 0 {
					fmt.Println("\tClosing old file")
					cur_file_writer.Flush()
					cur_file_writer.Close()
					cur_file.Close()
				}
				cur_filename = filepath.Join(outdir, fmt.Sprintf("%08d.gz", cur_idx))
				fmt.Println("New File:", cur_filename)
				if cur_file, err = gocommons.Open(cur_filename, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, gocommons.GZ_TRUE); err != nil {
					fmt.Fprintln(os.Stderr, "Could not open:", cur_filename, " :", err)
					return
				}
				if cur_file_writer, err = cur_file.Writer(0); err != nil {
					fmt.Fprintln(os.Stderr, "Could not get writer:", cur_filename, " :", err)
					return
				}
			}
			if cur_line_count == lines_per_file {
				fmt.Println("Rotating to new file ...")
				cur_idx++
				cur_line_count = 0
				// We haven't read a line yet. So we can re-enter the loop here
				continue
			}
			if line, ok := <-channel; !ok {
				cur_file_writer.Flush()
				cur_file_writer.Close()
				cur_file.Close()
				break
			} else {
				cur_file_writer.Write([]byte(line + "\n"))
				cur_line_count++
			}
		}
	}

	for _, file_path := range files {
		if infile_raw, err = gocommons.Open(file_path, os.O_RDONLY, gocommons.GZ_TRUE); err != nil {
			fmt.Fprintln(os.Stderr, "Failed to open:", file_path, ":", err)
			return
		}
		defer infile_raw.Close()
		if reader, err = infile_raw.Reader(0); err != nil {
			fmt.Fprintln(os.Stderr, "Could not get reader:", file_path)
			return
		}

		reader.Split(bufio.ScanLines)
		for reader.Scan() {
			line := reader.Text()
			logline := cpuprof.ParseLogline(line)
			boot_id := logline.BootId
			if _, ok := bootid_channel_map[boot_id]; !ok {
				// Create consumer
				bootid_channel_map[boot_id] = make(chan string, 100000)
				go boot_id_consumer(boot_id, bootid_channel_map[boot_id])

			} else {
				// Write line to channel
				bootid_channel_map[boot_id] <- line
			}
		}
	}
	// Done reading the file. Now close the channels
	for boot_id := range bootid_channel_map {
		close(bootid_channel_map[boot_id])
	}
	// Wait for all consumers to finish
	wg.Wait()
}

func StitchMain(args []string) {
	kingpin.MustParse(kpin.Parse(args[1:]))
	Process(*path, *regex, *j, *bufsize)
}

func main() {
	StitchMain(os.Args)
}

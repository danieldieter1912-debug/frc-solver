// frc CLI — liest JSON Puzzle-Response von stdin, gibt Solution-String aus
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"runtime"

	"frc-solver/frc"
)

func main() {
	workers := flag.Int("workers", runtime.NumCPU(), "Parallele Worker")
	verbose := flag.Bool("v", false, "Verbose")
	flag.Parse()

	data, err := io.ReadAll(os.Stdin)
	if err != nil || len(data) == 0 {
		fmt.Fprintln(os.Stderr, "❌ Keine Puzzle-Response auf stdin")
		os.Exit(1)
	}

	puzzle, err := frc.ParseResponse(data)
	if err != nil {
		// Vielleicht direkt der puzzle-String?
		puzzle, err = frc.ParsePuzzle(string(data))
		if err != nil {
			fmt.Fprintf(os.Stderr, "❌ Parse Fehler: %v\n", err)
			os.Exit(1)
		}
	}

	if *verbose {
		fmt.Fprintf(os.Stderr, "Puzzle: v=%d diff=%d n_puzzles=%d expiry=%dmin\n",
			puzzle.Version, puzzle.Difficulty, len(puzzle.Puzzles), puzzle.ExpiryMin)
	}

	sol, err := frc.SolveWorkers(puzzle, *workers)
	if err != nil {
		fmt.Fprintf(os.Stderr, "❌ Solve Fehler: %v\n", err)
		os.Exit(1)
	}

	if *verbose {
		fmt.Fprintf(os.Stderr, "Gelöst in %dms | Nonces: %v\n", sol.Took, sol.Nonces)
	}

	fmt.Println(sol.ToSolutionString())
}

func init() {
	// Für JSON-Output wenn -json Flag gesetzt
	_ = json.Marshal
}

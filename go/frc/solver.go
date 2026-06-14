// Package frc implements a Friendly Captcha v1 Proof-of-Work Solver.
//
// Protokoll:
//  1. GET /api/v1/puzzle?sitekey=... → {puzzle: base64, signature: hex}
//  2. Puzzle binary parsen
//  3. Für jedes Sub-Puzzle (8 Bytes): SHA256 Brute-Force mit führenden Null-Bits
//  4. Solution = base64(nonces) + "." + original_puzzle_b64
package frc

import (
	"crypto/sha256"
	"encoding/base64"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"runtime"
	"strings"
	"sync"
	"time"
)

// Puzzle enthält das geparste Friendly Captcha Puzzle.
type Puzzle struct {
	RawB64    string
	RawBytes  []byte
	Version   uint8
	Difficulty uint8   // Anzahl führender Null-Bits
	Timestamp uint32
	AccountID [4]byte
	AppID     [4]byte
	ExpiryMin uint16
	Puzzles   [][]byte // Liste der 8-Byte Sub-Puzzles
}

// Solution enthält die gelösten Nonces.
type Solution struct {
	Puzzle *Puzzle
	Nonces []int32  // 4-Byte Nonces (little-endian) für jedes Sub-Puzzle
	Took   int64    // Millisekunden
}

// ToSolutionString gibt den Solution-String zurück.
// Format: {base64(nonces)}.{puzzle_b64}
func (s *Solution) ToSolutionString() string {
	nonceBytes := make([]byte, len(s.Nonces)*4)
	for i, n := range s.Nonces {
		binary.LittleEndian.PutUint32(nonceBytes[i*4:], uint32(n))
	}
	return base64.StdEncoding.EncodeToString(nonceBytes) + "." + s.Puzzle.RawB64
}

// ParsePuzzle parst einen base64-kodierten Puzzle-String.
func ParsePuzzle(b64Str string) (*Puzzle, error) {
	// Padding ergänzen
	padding := (4 - len(b64Str)%4) % 4
	padded  := b64Str + strings.Repeat("=", padding)

	raw, err := base64.StdEncoding.DecodeString(padded)
	if err != nil {
		return nil, fmt.Errorf("base64 decode: %w", err)
	}
	if len(raw) < 17 {
		return nil, fmt.Errorf("puzzle too short: %d bytes", len(raw))
	}

	nPuzzles := int(raw[16])
	if len(raw) < 17+nPuzzles*8 {
		return nil, fmt.Errorf("puzzle data too short for %d sub-puzzles", nPuzzles)
	}

	puzzles := make([][]byte, nPuzzles)
	for i := 0; i < nPuzzles; i++ {
		start := 17 + i*8
		chunk := make([]byte, 8)
		copy(chunk, raw[start:start+8])
		puzzles[i] = chunk
	}

	p := &Puzzle{
		RawB64:     b64Str,
		RawBytes:   raw,
		Version:    raw[0],
		Difficulty: raw[1],
		Timestamp:  binary.BigEndian.Uint32(raw[2:6]),
		ExpiryMin:  binary.BigEndian.Uint16(raw[14:16]),
		Puzzles:    puzzles,
	}
	copy(p.AccountID[:], raw[6:10])
	copy(p.AppID[:], raw[10:14])

	return p, nil
}

// hasLeadingZeroBits prüft ob hash mindestens n führende Null-Bits hat.
func hasLeadingZeroBits(hash []byte, n int) bool {
	fullBytes    := n / 8
	remainingBits := n % 8

	for i := 0; i < fullBytes; i++ {
		if hash[i] != 0 {
			return false
		}
	}
	if remainingBits > 0 {
		mask := byte(0xFF << (8 - remainingBits))
		if hash[fullBytes]&mask != 0 {
			return false
		}
	}
	return true
}

// solveSubPuzzle löst ein einzelnes 8-Byte Sub-Puzzle.
func solveSubPuzzle(puzzleBytes []byte, difficulty int) (int32, error) {
	buf := make([]byte, 12) // 8 puzzle + 4 nonce
	copy(buf[:8], puzzleBytes)

	for n := int32(0); n < 0x7FFFFFFF; n++ {
		binary.LittleEndian.PutUint32(buf[8:], uint32(n))
		h := sha256.Sum256(buf)
		if hasLeadingZeroBits(h[:], difficulty) {
			return n, nil
		}
	}
	return 0, fmt.Errorf("no solution found")
}

// Solve löst alle Sub-Puzzles parallel (ein Goroutine pro Sub-Puzzle).
func Solve(puzzle *Puzzle) (*Solution, error) {
	return SolveWorkers(puzzle, runtime.NumCPU())
}

// SolveWorkers löst mit parallelen Goroutinen.
// Da Sub-Puzzles unabhängig sind, wird jedes Sub-Puzzle parallel gelöst.
func SolveWorkers(puzzle *Puzzle, workers int) (*Solution, error) {
	t0     := time.Now()
	n      := len(puzzle.Puzzles)
	nonces := make([]int32, n)
	errs   := make([]error, n)

	// Semaphore für max. workers gleichzeitige Goroutinen
	sem := make(chan struct{}, workers)
	var wg sync.WaitGroup

	for i, subPuzzle := range puzzle.Puzzles {
		wg.Add(1)
		go func(idx int, sp []byte) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			nonce, err := solveSubPuzzle(sp, int(puzzle.Difficulty))
			nonces[idx] = nonce
			errs[idx]   = err
		}(i, subPuzzle)
	}
	wg.Wait()

	for _, err := range errs {
		if err != nil {
			return nil, err
		}
	}

	took := time.Since(t0).Milliseconds()
	if took < 1 {
		took = 1
	}

	return &Solution{
		Puzzle: puzzle,
		Nonces: nonces,
		Took:   took,
	}, nil
}

// PuzzleResponse ist die JSON-Antwort vom Friendly Captcha API.
type PuzzleResponse struct {
	Puzzle    string `json:"puzzle"`
	Signature string `json:"signature"`
	Expires   string `json:"expires"`
}

// ParseResponse parst die JSON-Antwort und gibt ein Puzzle zurück.
func ParseResponse(jsonData []byte) (*Puzzle, error) {
	var resp PuzzleResponse
	if err := json.Unmarshal(jsonData, &resp); err != nil {
		return nil, fmt.Errorf("JSON parse: %w", err)
	}
	return ParsePuzzle(resp.Puzzle)
}

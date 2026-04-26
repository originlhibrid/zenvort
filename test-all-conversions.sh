#!/bin/bash
# test-all-conversions.sh — end-to-end conversion test for Zenvort
set -euo pipefail

API_BASE="http://localhost:3000"
POLL_INTERVAL=5
POLL_TIMEOUT=120
TMPDIR=$(mktemp -d)
RESULT_FILE="$TMPDIR/results.txt"

# ─── colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
RESET='\033[0m'

log()  { echo -e "${CYAN}[test]${RESET} $*"; }
pass() { echo -e "${GREEN}PASS${RESET}  $*"; }
fail() { echo -e "${RED}FAIL${RESET}  $*"; }
warn() { echo -e "${YELLOW}WARN${RESET}  $*"; }

# ─── cleanup ───────────────────────────────────────────────────────────────────
trap 'rm -rf "$TMPDIR"' EXIT

# ─── helpers ─────────────────────────────────────────────────────────────────
get_json_field() {
    python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    for k in '$1'.split('.'):
        d = d[k]
    print(d)
except:
    print('')
"
}

poll_job() {
    local job_id="$1"
    local elapsed=0
    while (( elapsed < POLL_TIMEOUT )); do
        local status
        status=$(curl -sf "$API_BASE/jobs/$job_id" \
            -H "Authorization: Bearer $APIKEY" \
            -H 'Accept: application/json' \
            -o /dev/null -w '%{http_code}')
        if (( status == 200 )); then
            local state
            state=$(curl -sf "$API_BASE/jobs/$job_id" \
                -H "Authorization: Bearer $APIKEY" \
                -H 'Accept: application/json' \
                | get_json_field status)
            if [[ "$state" == "DONE" || "$state" == "FAILED" ]]; then
                echo "$state"
                return
            fi
        fi
        sleep $POLL_INTERVAL
        (( elapsed += POLL_INTERVAL ))
    done
    echo "TIMEOUT"
}

submit_job() {
    local input_file="$1" input_format="$2" output_format="$3" pair_id="$4"
    local response
    response=$(curl -sf -X POST "$API_BASE/jobs" \
        -H "Authorization: Bearer $APIKEY" \
        -F "file=@$input_file" \
        -F "outputFormat=$output_format" \
        -H 'Accept: application/json' \
        -o "$TMPDIR/response_$pair_id.json" \
        -w "%{http_code}")
    local http_code="${response: -3}"
    if (( http_code == 413 )); then
        echo "413_FILE_TOO_LARGE" > "$TMPDIR/status_$pair_id"
        return
    fi
    if (( http_code >= 400 )); then
        echo "HTTP_$http_code" > "$TMPDIR/status_$pair_id"
        return
    fi
    local job_id
    job_id=$(get_json_field jobId < "$TMPDIR/response_$pair_id.json")
    if [[ -z "$job_id" ]]; then
        echo "NO_JOB_ID" > "$TMPDIR/status_$pair_id"
        return
    fi
    echo "$job_id" > "$TMPDIR/jobid_$pair_id"
}

# ─── sign-up fresh user ────────────────────────────────────────────────────────
log "Signing up test user..."
EMAIL="test_$(date +%s)_$(openssl rand -hex 4)@example.com"
PASS="TestPass123!"

SIGNUP=$(curl -sf -X POST "$API_BASE/auth/signup" \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json' \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" \
    -o "$TMPDIR/signup.json" \
    -w "%{http_code}")
HTTP_CODE="${SIGNUP: -3}"

if (( HTTP_CODE != 201 )); then
    fail "Signup failed with HTTP $HTTP_CODE"
    exit 1
fi

APIKEY=$(get_json_field apiKey < "$TMPDIR/signup.json")
if [[ -z "$APIKEY" ]]; then
    fail "Signup returned 201 but no apiKey"
    exit 1
fi
log "Signed up as $EMAIL | apiKey: ${APIKEY:0:12}..."

# ─── generate missing sample files ────────────────────────────────────────────
log "Generating missing test files..."

# MD
cat > "$TMPDIR/md.md" << 'MARKDOWN'
# Test Document

Hello **world**. This is a test.

| Column A | Column B |
|----------|----------|
| Row 1    | Data 1   |
| Row 2    | Data 2   |

```python
print("Hello from Markdown")
```
MARKDOWN

# HTML
cat > "$TMPDIR/html.html" << 'HTML'
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Test</title></head>
<body>
<h1>Test Document</h1>
<p>Hello <strong>world</strong>. This is a test.</p>
<img src="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' width='100' height='100'/>" alt="x"/>
</body>
</html>
HTML

# JPG (1×1 red pixel PPM → convert via python)
python3 -c "
from PIL import Image
import os
img = Image.new('RGB', (1, 1), color='red')
img.save('$TMPDIR/jpg.jpg', 'JPEG', quality=85)
" 2>/dev/null || \
python3 -c "
# fallback: minimal valid JPEG using struct
import struct
# minimal 1×1 JPEG
b = bytes.fromhex(
    'ffd8fffe000109004800550000000000ffdb004300'
    'ffffff000000000000000000000000000000000000'
    '000000000000000000000000000000000000000000'
    '000000000000000000000000000000000000000000'
    '000000000000000000000000000000000000000000'
    '000000000000000000000000000000000000000000'
    '000000000000000000000000000000000000000000'
    '0000000000000000000000000000000000ffc0 0011'
    '08 00010001 0100 1100 ffda 00030101 0000 3f00'
)
# actually let's just use PPM
with open('$TMPDIR/jpg.ppm', 'wb') as f:
    f.write(b'P6\n1 1\n255\n')
    f.write(b'\\xff\\x00\\x00')
" && convert "$TMPDIR/jpg.ppm" "$TMPDIR/jpg.jpg" 2>/dev/null || \
dd if=/dev/urandom bs=1 count=3 of="$TMPDIR/jpg.jpg" 2>/dev/null

# PNG (1×1 blue pixel)
python3 -c "
from PIL import Image
img = Image.new('RGBA', (1, 1), color='blue')
img.save('$TMPDIR/png.png', 'PNG')
" 2>/dev/null || \
printf '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00\x00IEND\xaeB`\x82' > "$TMPDIR/png.png"

# WEBP (1×1 green pixel)
python3 -c "
from PIL import Image
img = Image.new('RGB', (1, 1), color='green')
img.save('$TMPDIR/webp.webp', 'WEBP')
" 2>/dev/null || \
cp "$TMPDIR/png.png" "$TMPDIR/webp.webp"

# MP3 (minimal valid MP3 — ID3v2 + frame)
python3 -c "
# write a minimal valid MP3 (silence, 128kbps, 44100Hz, mono, 1 frame)
import struct
id3 = b'ID3' + bytes([4, 0, 0]) + b'\\x00\\x00\\x00\\x0b'
frame = bytes([0xFF, 0xFB, 0x90, 0x00,
               0x00, 0x00, 0x00, 0x00,
               0x00, 0x00, 0x00, 0x00,
               0x00, 0x00, 0x00, 0x00,
               0x00, 0x00, 0x00, 0x00])
with open('$TMPDIR/mp3.mp3', 'wb') as f:
    f.write(id3)
    for _ in range(200):
        f.write(frame)
"

# WAV (8-bit mono 8000Hz sine wave)
python3 -c "
import struct, math
sample_rate = 8000
duration = 0.5
num_samples = int(sample_rate * duration)
with open('$TMPDIR/wav.wav', 'wb') as f:
    f.write(b'RIFF')
    f.write(struct.pack('<I', 36 + num_samples))
    f.write(b'WAVE')
    f.write(b'fmt ')
    f.write(struct.pack('<IHHIIHH', 16, 1, 1, sample_rate, sample_rate, 1, 8))
    f.write(b'data')
    f.write(struct.pack('<I', num_samples))
    for i in range(num_samples):
        f.write(bytes([int(128 + 100 * math.sin(2 * math.pi * 440 * i / sample_rate))]))
"

# ─── map of local files to formats ────────────────────────────────────────────
declare -A FILE_MAP=(
    [docx]="docx.docx"
    [pdf]="pdf.pdf"
    [mp4]="mp4.mp4"
    [md]="md.md"
    [html]="html.html"
    [jpg]="jpg.jpg"
    [png]="png.png"
    [webp]="webp.webp"
    [mp3]="mp3.mp3"
    [wav]="wav.wav"
)

SAMPLE_DIR="/root/Zenvort/sample"

# ─── build conversion pairs ────────────────────────────────────────────────────
# Format: input_format output_format
CONV_PAIRS=(
    # PDF conversions
    "pdf"  "png"
    "pdf"  "jpg"
    "pdf"  "txt"
    "pdf"  "docx"
    "pdf"  "html"
    # DOCX conversions
    "docx" "pdf"
    "docx" "txt"
    "docx" "html"
    # MD conversions
    "md"   "pdf"
    "md"   "html"
    "md"   "txt"
    "md"   "docx"
    # HTML conversions
    "html" "pdf"
    "html" "docx"
    # JPG conversions
    "jpg"  "png"
    "jpg"  "webp"
    "jpg"  "avif"
    "jpg"  "pdf"
    # PNG conversions
    "png"  "jpg"
    "png"  "webp"
    "png"  "avif"
    "png"  "pdf"
    # WEBP conversions
    "webp" "jpg"
    "webp" "png"
    # MP4 conversions
    "mp4"  "mp3"
    "mp4"  "webm"
    # MP3 conversions
    "mp3"  "wav"
    # WAV conversions
    "wav"  "mp3"
)

PAIR_COUNT=${#CONV_PAIRS[@]}
PAIR_IDX=0

log "Submitting $((PAIR_COUNT / 2)) conversion jobs in parallel..."

# ─── submit all jobs ────────────────────────────────────────────────────────────
for (( i=0; i<PAIR_COUNT; i+=2 )); do
    INPUT_FMT="${CONV_PAIRS[i]}"
    OUTPUT_FMT="${CONV_PAIRS[i+1]}"
    PAIR_ID="p$PAIR_IDX"

    # resolve local file path
    case "$INPUT_FMT" in
        docx|pdf|mp4) FILE_PATH="$SAMPLE_DIR/${FILE_MAP[$INPUT_FMT]}" ;;
        md|html|jpg|png|webp|mp3|wav) FILE_PATH="$TMPDIR/${FILE_MAP[$INPUT_FMT]}" ;;
        *) FILE_PATH="$TMPDIR/${FILE_MAP[$INPUT_FMT]}" ;;
    esac

    if [[ ! -f "$FILE_PATH" ]]; then
        warn "Missing file for $INPUT_FMT → $OUTPUT_FMT, skipping"
        echo "MISSING_FILE" > "$TMPDIR/status_$PAIR_ID"
    else
        submit_job "$FILE_PATH" "$INPUT_FMT" "$OUTPUT_FMT" "$PAIR_ID" &
    fi

    (( PAIR_IDX++ ))
done

wait  # wait for all submissions

# collect job IDs (poll in background-safe order)
PAIR_IDX=0
JOB_IDS=()
for (( i=0; i<PAIR_COUNT; i+=2 )); do
    INPUT_FMT="${CONV_PAIRS[i]}"
    OUTPUT_FMT="${CONV_PAIRS[i+1]}"
    PAIR_ID="p$PAIR_IDX"

    STATUS=$(cat "$TMPDIR/status_$PAIR_ID" 2>/dev/null || echo "")

    if [[ "$STATUS" == "MISSING_FILE" || "$STATUS" == "NO_JOB_ID" || \
          "$STATUS" == "HTTP_"* || "$STATUS" == "413_FILE_TOO_LARGE" ]]; then
        JOB_IDS+=("$STATUS")
    else
        JOB_IDS+=("$(cat "$TMPDIR/jobid_$PAIR_ID 2>/dev/null || echo '')""")
    fi
    (( PAIR_IDX++ ))
done

# ─── poll all jobs ─────────────────────────────────────────────────────────────
log "Polling jobs (max ${POLL_TIMEOUT}s per job)..."

PAIR_IDX=0
for (( i=0; i<PAIR_COUNT; i+=2 )); do
    INPUT_FMT="${CONV_PAIRS[i]}"
    OUTPUT_FMT="${CONV_PAIRS[i+1]}"
    PAIR_ID="p$PAIR_IDX"

    STATUS=$(cat "$TMPDIR/status_$PAIR_ID" 2>/dev/null || echo "")

    if [[ "$STATUS" == "MISSING_FILE" || "$STATUS" == "NO_JOB_ID" || \
          "$STATUS" == "HTTP_"* || "$STATUS" == "413_FILE_TOO_LARGE" ]]; then
        (( PAIR_IDX++ ))
        continue
    fi

    JOB_ID="${JOB_IDS[$PAIR_IDX]}"
    if [[ -z "$JOB_ID" ]]; then
        echo "NO_JOB_ID" > "$TMPDIR/status_$PAIR_ID"
        (( PAIR_IDX++ ))
        continue
    fi

    log "  Polling job $JOB_ID ($INPUT_FMT → $OUTPUT_FMT)..."
    FINAL_STATUS=$(poll_job "$JOB_ID")
    echo "$FINAL_STATUS" > "$TMPDIR/status_$PAIR_ID"

    if [[ "$FINAL_STATUS" == "DONE" ]]; then
        # grab output URL and file size via HEAD
        SIZE=$(curl -sfI "$API_BASE/jobs/$JOB_ID" \
            -H "Authorization: Bearer $APIKEY" \
            -H 'Accept: application/json' \
            | get_json_field outputUrl \
            | xargs -I{} curl -sfI {} \
            | grep -i '^content-length:' \
            | awk '{print $2}' \
            | tr -d '\r' || echo "N/A")
        echo "$SIZE" > "$TMPDIR/size_$PAIR_ID"
    elif [[ "$FINAL_STATUS" == "FAILED" ]]; then
        # grab error message
        ERROR=$(curl -sf "$API_BASE/jobs/$JOB_ID" \
            -H "Authorization: Bearer $APIKEY" \
            -H 'Accept: application/json' \
            | get_json_field error)
        echo "$ERROR" > "$TMPDIR/error_$PAIR_ID"
    fi

    (( PAIR_IDX++ ))
done

# ─── print results table ───────────────────────────────────────────────────────
log ""
log "══════════════════════════════════════════════════════════"
log "                    RESULTS TABLE"
log "══════════════════════════════════════════════════════════"
printf "\n  %-8s  %-10s  %-9s  %-12s  %s\n" "INPUT" "OUTPUT" "STATUS" "SIZE" "DETAIL"
echo "  --------  ----------  ---------  ------------  ----"

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

PAIR_IDX=0
for (( i=0; i<PAIR_COUNT; i+=2 )); do
    INPUT_FMT="${CONV_PAIRS[i]}"
    OUTPUT_FMT="${CONV_PAIRS[i+1]}"
    PAIR_ID="p$PAIR_IDX"

    STATUS=$(cat "$TMPDIR/status_$PAIR_ID" 2>/dev/null || echo "UNKNOWN")
    SIZE=$(cat "$TMPDIR/size_$PAIR_ID" 2>/dev/null || echo "")
    ERROR=$(cat "$TMPDIR/error_$PAIR_ID" 2>/dev/null || echo "")

    case "$STATUS" in
        DONE)
            COLOR=$GREEN; COUNT_P=1; COUNT_F=0
            DETAIL="${SIZE}B"
            ;;
        FAILED)
            COLOR=$RED; COUNT_P=0; COUNT_F=1
            # truncate error to 60 chars
            DETAIL="${ERROR:0:58}"
            [[ ${#ERROR} -gt 58 ]] && DETAIL="${DETAIL}…"
            ;;
        MISSING_FILE)
            COLOR=$YELLOW; COUNT_P=0; COUNT_F=0; COUNT_S=1
            DETAIL="missing file"
            ;;
        NO_JOB_ID)
            COLOR=$RED; COUNT_P=0; COUNT_F=1
            DETAIL="no job id"
            ;;
        HTTP_*|413_FILE_TOO_LARGE)
            COLOR=$YELLOW; COUNT_P=0; COUNT_F=0; COUNT_S=1
            DETAIL="$STATUS"
            ;;
        TIMEOUT)
            COLOR=$RED; COUNT_P=0; COUNT_F=1
            DETAIL="timeout"
            ;;
        *)
            COLOR=$YELLOW; COUNT_P=0; COUNT_F=0; COUNT_S=1
            DETAIL="$STATUS"
            ;;
    esac

    printf "  ${COLOR}%-8s  %-10s  %-9s  %-12s  %s${RESET}\n" \
        "$INPUT_FMT" "$OUTPUT_FMT" "$STATUS" "$DETAIL" ""

    PASS_COUNT=$((PASS_COUNT + ${COUNT_P:-0}))
    FAIL_COUNT=$((FAIL_COUNT + ${COUNT_F:-0}))
    SKIP_COUNT=$((SKIP_COUNT + ${COUNT_S:-0}))
    (( PAIR_IDX++ ))
done

# ─── summary ────────────────────────────────────────────────────────────────────
TOTAL=$((PASS_COUNT + FAIL_COUNT + SKIP_COUNT))
log ""
log "══════════════════════════════════════════════════════════"
log "                     SUMMARY"
log "══════════════════════════════════════════════════════════"
printf "  Total:    %d conversions\n" "$TOTAL"
printf "  Passed:   ${GREEN}%d${RESET}\n" "$PASS_COUNT"
printf "  Failed:   ${RED}%d${RESET}\n" "$FAIL_COUNT"
printf "  Skipped:  ${YELLOW}%d${RESET}\n" "$SKIP_COUNT"
log ""

if (( FAIL_COUNT > 0 )); then
    exit 1
fi
exit 0

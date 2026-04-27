#!/bin/bash
# test-all-conversions.sh — end-to-end conversion test for Zenvort
set -euo pipefail

API_BASE="http://localhost:3000"
POLL_INTERVAL=5
POLL_TIMEOUT=120
TMPDIR=$(mktemp -d)
RESULT_FILE="$TMPDIR/results.txt"
TEST_DIR="${TEST_DIR:-/tmp/zenvort-test}"

# ─── colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
RESET='\033[0m'

log()  { echo -e "${CYAN}[test]${RESET} $*"; }
pass() { echo -e "${GREEN}PASS${RESET}  $*"; }
fail() { echo -e "${RED}FAIL${RESET}  $*"; }
warn() { echo -e "${YELLOW}WARN${RESET}  $*"; }

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

check_sample() {
    local fmt=$1
    if [ ! -s "$TEST_DIR/sample.$fmt" ]; then
        echo "[setup] WARNING: Missing sample.$fmt — skipping routes for $fmt"
        return 1
    fi
    return 0
}

# ─── sign-up fresh user ────────────────────────────────────────────────────────
log "Signing up test user..."
EMAIL="test_$(date +%s)_$(openssl rand -hex 4)@example.com"
PASS="TestPass123!"

# Retry signup up to 5 times on rate limiting (wait 5 seconds between retries)
SIGNUP=""
HTTP_CODE=""
for attempt in 1 2 3 4 5; do
    if [[ $attempt -gt 1 ]]; then
        echo "[setup] Retry signup attempt $attempt (waiting 5s)..."
        sleep 5
    fi
    
    SIGNUP=$(curl -sf -X POST "$API_BASE/auth/signup" \
        -H 'Content-Type: application/json' \
        -H 'Accept: application/json' \
        -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" \
        -o "$TMPDIR/signup.json" \
        -w "%{http_code}") 2>/dev/null || true
    
    HTTP_CODE="${SIGNUP: -3}"
    
    if [[ "$HTTP_CODE" == "201" ]]; then
        break
    fi
    
    if [[ "$HTTP_CODE" == "429" ]]; then
        echo "[setup] Rate limited (429), will retry..."
        continue
    fi
done

if (( HTTP_CODE != 201 )); then
    fail "Signup failed with HTTP $HTTP_CODE"
    exit 1
fi

APIKEY=$(get_json_field apiKey < "$TMPDIR/signup.json")
USER_ID=$(get_json_field id < "$TMPDIR/signup.json")
if [[ -z "$APIKEY" ]]; then
    fail "Signup returned 201 but no apiKey"
    exit 1
fi
log "Signed up as $EMAIL | apiKey: ${APIKEY:0:12}..."

# ─── CHANGE 5: Credit top-up at start ─────────────────────────────────────────
echo "[setup] Topping up credits to 500..."
docker exec zenvort-postgres psql -U zenvort -d zenvort \
  -c "UPDATE users SET credits = 500 WHERE id = '$USER_ID';" 2>/dev/null || true

# ─── CHANGE 1: Check real sample files ─────────────────────────────────────────
log "Checking real sample files at $TEST_DIR..."

REQUIRED_SAMPLES="pdf docx mp4 jpg png webp epub mp3 wav xlsx pptx odt gif"
for fmt in $REQUIRED_SAMPLES; do
    check_sample "$fmt" || true
done

# ─── CHANGE 2: Derive additional formats from real samples ─────────────────────
echo "[setup] Deriving additional formats from real samples..."

# Images — derive from real jpg
if [ -s "$TEST_DIR/sample.jpg" ]; then
    python3 -c "from PIL import Image; Image.open('$TEST_DIR/sample.jpg').save('$TEST_DIR/sample.avif')" 2>/dev/null || true
    python3 -c "from PIL import Image; Image.open('$TEST_DIR/sample.jpg').save('$TEST_DIR/sample.bmp')" 2>/dev/null || true
    python3 -c "from PIL import Image; Image.open('$TEST_DIR/sample.jpg').save('$TEST_DIR/sample.tiff')" 2>/dev/null || true
    echo "[setup] Derived avif, bmp, tiff from jpg"
fi

# Video — derive from real mp4 (first 5 seconds only)
if [ -s "$TEST_DIR/sample.mp4" ]; then
    ffmpeg -i "$TEST_DIR/sample.mp4" -t 5 -y "$TEST_DIR/sample.avi" 2>/dev/null || true
    ffmpeg -i "$TEST_DIR/sample.mp4" -t 5 -y "$TEST_DIR/sample.mov" 2>/dev/null || true
    ffmpeg -i "$TEST_DIR/sample.mp4" -t 5 -y "$TEST_DIR/sample.webm" 2>/dev/null || true
    echo "[setup] Derived avi, mov, webm from mp4"
fi

# Audio — derive from real mp3 (first 5 seconds only)
if [ -s "$TEST_DIR/sample.mp3" ]; then
    ffmpeg -i "$TEST_DIR/sample.mp3" -t 5 -y "$TEST_DIR/sample.ogg" 2>/dev/null || true
    ffmpeg -i "$TEST_DIR/sample.mp3" -t 5 -y "$TEST_DIR/sample.flac" 2>/dev/null || true
    echo "[setup] Derived ogg, flac from mp3"
fi

# ─── CHANGE 3: Generate plain text formats from scratch ────────────────────────
echo "[setup] Generating plain text formats..."

echo "# Test Heading" > "$TEST_DIR/sample.md"
echo "" >> "$TEST_DIR/sample.md"
echo "Hello Zenvort conversion test." >> "$TEST_DIR/sample.md"

echo "<html><body><h1>Test</h1><p>Hello Zenvort</p></body></html>" > "$TEST_DIR/sample.html"
echo "Hello Zenvort conversion test" > "$TEST_DIR/sample.txt"
printf "name,age,city\nAlice,30,London\nBob,25,Paris\n" > "$TEST_DIR/sample.csv"
printf '{\rtf1\ansi\deff0 Hello Zenvort}' > "$TEST_DIR/sample.rtf"

echo "[setup] Generated md, html, txt, csv, rtf"

# ─── map of local files to formats ────────────────────────────────────────────
declare -A FILE_MAP=(
    [docx]="docx"
    [pdf]="pdf"
    [mp4]="mp4"
    [mp3]="mp3"
    [wav]="wav"
    [epub]="epub"
    [xlsx]="xlsx"
    [pptx]="pptx"
    [odt]="odt"
    [gif]="gif"
    [md]="md"
    [html]="html"
    [jpg]="jpg"
    [png]="png"
    [webp]="webp"
    [txt]="txt"
    [csv]="csv"
    [rtf]="rtf"
    [avif]="avif"
    [bmp]="bmp"
    [tiff]="tiff"
    [avi]="avi"
    [mov]="mov"
    [webm]="webm"
    [ogg]="ogg"
    [flac]="flac"
)

SAMPLE_DIR="$TEST_DIR"

# ─── build conversion pairs ────────────────────────────────────────────────────
# Format: input_format output_format
CONV_PAIRS=(
    # PDF conversions
    "pdf"  "png"
    "pdf"  "jpg"
    "pdf"  "txt"
    "pdf"  "docx"
    "pdf"  "html"
    "pdf"  "rtf"
    # DOCX conversions
    "docx" "pdf"
    "docx" "txt"
    "docx" "html"
    "docx" "rtf"
    # MD conversions
    "md"   "pdf"
    "md"   "html"
    "md"   "txt"
    "md"   "docx"
    "md"   "rtf"
    # HTML conversions
    "html" "pdf"
    "html" "docx"
    "html" "txt"
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
    PAIR_ID="p$((i/2))"
    INPUT_FMT="${CONV_PAIRS[i]}"
    OUTPUT_FMT="${CONV_PAIRS[i+1]}"

    # resolve local file path
    FILE_PATH="$SAMPLE_DIR/sample.${FILE_MAP[$INPUT_FMT]}"

    if [[ ! -f "$FILE_PATH" ]]; then
        warn "Missing file for $INPUT_FMT → $OUTPUT_FMT, skipping"
        echo "MISSING_FILE" > "$TMPDIR/status_$PAIR_ID"
    else
        submit_job "$FILE_PATH" "$INPUT_FMT" "$OUTPUT_FMT" "$PAIR_ID" &
    fi

    (( PAIR_IDX++ )) || true
done
wait  # wait for all submissions

PAIR_IDX=0
JOB_IDS=()
for (( i=0; i<PAIR_COUNT; i+=2 )); do
    INPUT_FMT="${CONV_PAIRS[i]}"
    OUTPUT_FMT="${CONV_PAIRS[i+1]}"
    PAIR_ID="p$((i/2))"

    STATUS=$(cat "$TMPDIR/status_$PAIR_ID" 2>/dev/null || echo "")

    if [[ "$STATUS" == "MISSING_FILE" || "$STATUS" == "NO_JOB_ID" || \
          "$STATUS" == "HTTP_"* || "$STATUS" == "413_FILE_TOO_LARGE" ]]; then
        JOB_IDS+=("$STATUS")
    else
        JOB_IDS+=("$(cat "$TMPDIR/jobid_$PAIR_ID" 2>/dev/null || echo "")")
    fi
    (( PAIR_IDX++ )) || true
done

# ─── poll all jobs ─────────────────────────────────────────────────────────────
log "Polling jobs (max ${POLL_TIMEOUT}s per job)..."

PAIR_IDX=0
for (( i=0; i<PAIR_COUNT; i+=2 )); do
    INPUT_FMT="${CONV_PAIRS[i]}"
    OUTPUT_FMT="${CONV_PAIRS[i+1]}"
    PAIR_ID="p$((i/2))"

    STATUS=$(cat "$TMPDIR/status_$PAIR_ID" 2>/dev/null || echo "")

    if [[ "$STATUS" == "MISSING_FILE" || "$STATUS" == "NO_JOB_ID" || \
          "$STATUS" == "HTTP_"* || "$STATUS" == "413_FILE_TOO_LARGE" ]]; then
        (( PAIR_IDX++ )) || true
        continue
    fi

    JOB_ID="${JOB_IDS[$PAIR_IDX]}"
    if [[ -z "$JOB_ID" ]]; then
        echo "NO_JOB_ID" > "$TMPDIR/status_$PAIR_ID"
        (( PAIR_IDX++ )) || true
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

    (( PAIR_IDX++ )) || true
done

# ─── print results table ────────────────────────────────────────────────────────
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
    PAIR_ID="p$((i/2))"

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
    (( PAIR_IDX++ )) || true
done

# ─── CHANGE 4: Cleanup (only output files, keep sample files) ───────────────────
trap "rm -f $TMPDIR/*" EXIT

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
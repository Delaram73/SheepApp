jobs:
  run:
    runs-on: ubuntu-latest
    env:
      GITHUB_PAT: ${{ secrets.GITHUB_TOKEN }}

    steps:
      - name: Check out repo
        uses: actions/checkout@v4

      - name: Set up R
        uses: r-lib/actions/setup-r@v2
        with:
          use-public-rspm: true

      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y --no-install-recommends unzip

      - name: Install R packages (CRAN)
        run: |
          Rscript -e 'repos <- c(CRAN="https://cloud.r-project.org"); install.packages(c("read.gt3x"), repos = repos, Ncpus = parallel::detectCores())'

      - name: Locate converter script
        id: find_script
        shell: bash
        run: |
          set -euo pipefail
          script_path="$(git ls-files | grep -E '(^|/)convert_gt3x_to_csv\.R$' | head -n1 || true)"
          if [[ -z "${script_path}" ]]; then
            echo "❌ Could not find convert_gt3x_to_csv.R anywhere in the repo."
            exit 1
          fi
          echo "Found script at: ${script_path}"
          echo "script=${script_path}" >> "$GITHUB_OUTPUT"

      - name: Run converter
        env:
          DATA_DIR: ${{ github.workspace }}/data   # your script can read this if it supports it
        run: |
          set -euo pipefail
          mkdir -p data
          echo "Workspace: ${{ github.workspace }}"
          echo "PWD: $(pwd)"
          echo "R version:"
          Rscript -e 'sessionInfo()'
          echo "Running: Rscript '${{ steps.find_script.outputs.script }}'"
          Rscript "${{ steps.find_script.outputs.script }}"

      - name: Collect CSVs into data/
        shell: bash
        run: |
          set -euo pipefail
          echo "--- searching for CSVs in repo ---"
          find . -type f -name '*.csv' -not -path './.git/*' -printf '%p\t%k KB\n' || true
          echo "--- moving CSVs into ./data ---"
          # Move any found CSVs (if none, this does nothing)
          mapfile -t csvs < <(find . -type f -name '*.csv' -not -path './.git/*' || true)
          if (( ${#csvs[@]} > 0 )); then
            mkdir -p data
            for f in "${csvs[@]}"; do
              # preserve filename only; if you want to keep subfolders, adjust as needed
              dest="data/$(basename "$f")"
              if [[ "$f" != "$dest" ]]; then
                mv -f "$f" "$dest"
              fi
            done
          fi
          echo "--- final data/ listing ---"
          ls -lh data || true

      - name: Upload converted CSVs (artifact)
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: converted-csvs
          path: data/*.csv
          if-no-files-found: warn

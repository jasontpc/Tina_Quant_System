# Parse S&P 500 wikitext to extract GICS sectors
import re

with open('sp500_wikitext.txt', 'r', encoding='utf-8') as f:
    wikitext = f.read()

lines = wikitext.split('\n')

sector_tickers = {}
current_ticker = None

for i, line in enumerate(lines):
    line = line.strip()
    
    # Match ticker line like:|{{NyseSymbol|MMM}} or | {{NasdaqSymbol|ADBE}}
    ticker_match = re.match(r'\|\{\{(NyseSymbol|NasdaqSymbol)\|(.+?)\}\}', line)
    if ticker_match:
        current_ticker = ticker_match.group(2)
        # Check next line for sector
        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            # Pattern: |[[Company]]|| Sector || ...
            sector_match = re.search(r'\|\|\s*([^\|]+?)\s*\|\|', next_line)
            if sector_match and current_ticker:
                sector = sector_match.group(1).strip()
                # Only use actual GICS sectors (not sub-industries, etc.)
                if sector in ['Industrials', 'Health Care', 'Information Technology', 
                              'Utilities', 'Financials', 'Materials', 
                              'Consumer Discretionary', 'Real Estate', 
                              'Communication Services', 'Consumer Staples', 'Energy']:
                    if sector not in sector_tickers:
                        sector_tickers[sector] = []
                    if current_ticker not in sector_tickers[sector]:
                        sector_tickers[sector].append(current_ticker)

# Write to output file
with open('sp500_sectors_output.txt', 'w', encoding='utf-8') as f:
    total = 0
    for sector, tickers in sorted(sector_tickers.items()):
        f.write(f'\n=== {sector} ({len(tickers)} stocks) ===\n')
        f.write(str(sorted(tickers)) + '\n')
        total += len(tickers)
    f.write(f'\n\nTOTAL: {total} stocks across {len(sector_tickers)} sectors\n')

print("Done!")
print(f"Sectors: {list(sector_tickers.keys())}")
print(f"Total: {sum(len(v) for v in sector_tickers.values())} stocks")
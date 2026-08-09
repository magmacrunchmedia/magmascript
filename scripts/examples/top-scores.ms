# top-scores.ms — Example magmascript script (future DSL)
#
# This file shows what .ms scripts might look like in Phase 3.
# Currently for reference only — the DSL interpreter is not yet implemented.

# Fetch all scoreboards
boards = mcp.scoreboards()

# Print games with more than 5 entries
for board in boards:
    if board.entries > 5:
        print(f"{board.game}: {board.entries} entries, top score: {board.top.score}")

# Search for artists
artists = mcp.search("aphex twin")
for artist in artists:
    print(f"Found: {artist.name} ({artist.type})")

# Check Pi status
status = mcp.pi_status()
down = [s for s in status if not s.ok]
if down:
    print(f"WARNING: {len(down)} services down!")
    for s in down:
        print(f"  ✗ {s.name}: {s.status}")
else:
    print("All services running.")

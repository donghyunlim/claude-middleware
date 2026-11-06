import argparse, sqlite3, pathlib
ap = argparse.ArgumentParser(); ap.add_argument("--db", required=True); a = ap.parse_args()
con = sqlite3.connect(a.db)
con.execute("create table if not exists _migrations(name text primary key)")
done = {r[0] for r in con.execute("select name from _migrations")}
for f in sorted(pathlib.Path(__file__).parent.joinpath("migrations").glob("*.sql")):
    if f.name in done:
        continue
    con.executescript(f.read_text())
    con.execute("insert into _migrations values (?)", (f.name,))
    print("applied", f.name)
con.commit()

import shutil, sqlite3, subprocess, sys, os
root = sys.argv[1]
here = os.path.dirname(os.path.abspath(__file__))
shutil.copytree(os.path.join(here, "fixture"), root, dirs_exist_ok=True)
os.makedirs(os.path.join(root, "db"), exist_ok=True)
for name, n in [("prod.db", 500), ("dev.db", 20)]:
    p = os.path.join(root, "db", name)
    subprocess.run([sys.executable, os.path.join(root, "migrate.py"), "--db", p], check=True, capture_output=True)
    con = sqlite3.connect(p)
    con.executemany("insert into users(email, legacy_phone, phone) values (?,?,?)",
                    [(f"u{i}@ex.com", f"010-{i:04d}-0000" if i % 7 == 0 else None, f"010-{i:04d}-1111") for i in range(n)])
    con.commit(); con.close()

import argparse
from .orders import load_orders, order_total, STATUS_LABEL


def main(argv=None):
    ap = argparse.ArgumentParser(prog="shop")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    a = ap.parse_args(argv)
    if a.cmd == "list":
        for o in load_orders():
            print(o["id"], o["created_at"], STATUS_LABEL[o["status"]], order_total(o))


if __name__ == "__main__":
    main()

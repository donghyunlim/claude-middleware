import sys

from crmkit._backend import FakeBackend
from crmkit.sample_data import SAMPLE

from . import billing, notify, reports


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    b = FakeBackend(SAMPLE)
    if argv[:1] == ["report"]:
        for m, n in reports.monthly_signups(b).items():
            print(m, n)
    elif argv[:1] == ["invoice"]:
        print(billing.invoice_header(b, argv[1], argv[2]))
    elif argv[:1] == ["notify"]:
        print("\n".join(notify.renewal_messages(b, argv[1:])))
    else:
        print("usage: python3 -m app.cli report | invoice CID YYYY-MM | notify CID...")


if __name__ == "__main__":
    main()

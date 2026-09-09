"""Estimated model cost guard, not a Claude subscription quota meter."""
from datetime import datetime
try:
    from .ledger import Ledger
except ImportError:
    from ledger import Ledger


class BudgetRefused(ValueError):
    pass


def spend_today(ledger=None):
    today = datetime.now().astimezone().date()
    return sum(r["cost_usd"] for r in (ledger or Ledger()).records()
               if datetime.fromisoformat(r["created_at"]).astimezone().date() == today)


def spend_total(ledger=None):
    return sum(r["cost_usd"] for r in (ledger or Ledger()).records())


def check(ceiling, ledger=None, force=False):
    spent = spend_today(ledger)
    if not force and spent >= ceiling:
        raise BudgetRefused(f"Daily estimated cost ${spent:.4f} reached ${ceiling:.2f}; "
                            f"${max(0, spent-ceiling):.4f} over. --force overrides one run.")
    return max(0.0, ceiling - spent)

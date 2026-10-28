"""Run a small, entirely offline game-theory sanity demonstration."""
from .kuhn import KuhnCFR, expected_p0


def main() -> None:
    solver = KuhnCFR()
    solver.train(10_000)
    print(f"Kuhn CFR expected P0 payoff: {expected_p0(solver.policy()):.5f}")
    print("Reference two-player Kuhn game; not Sequoia variant or win-rate estimate.")


if __name__ == "__main__":
    main()

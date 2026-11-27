"""Run:  python -m timetable.main --solver heuristic|cpsat --out output"""
import argparse, os, time
from .sample_data import build_sample
from .validator import validate
from .exporter import to_json, to_excel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solver", choices=["heuristic", "cpsat"], default="heuristic")
    ap.add_argument("--time-limit", type=int, default=60, help="seconds (cpsat only)")
    ap.add_argument("--out", default="output")
    args = ap.parse_args()

    problem = build_sample()
    t0 = time.time()
    if args.solver == "cpsat":
        from .solver_cpsat import solve_cpsat
        entries = solve_cpsat(problem, args.time_limit)
    else:
        from .solver_heuristic import solve_heuristic
        entries = solve_heuristic(problem)
    if not entries:
        print("No feasible timetable found. Relax constraints (more rooms/teachers/slots).")
        return
    hard, soft = validate(problem, entries)
    print(f"Solver: {args.solver} | sessions placed: {len(entries)} | time: {time.time()-t0:.2f}s")
    print(f"Hard-constraint violations: {len(hard)}")
    for h in hard: print("  !", h)
    print(f"Soft warnings: {len(soft)}")
    for s in soft[:10]: print("  ~", s)
    os.makedirs(args.out, exist_ok=True)
    to_json(problem, entries, f"{args.out}/timetable.json")
    to_excel(problem, entries, f"{args.out}/timetable.xlsx")
    print(f"Saved to {args.out}/timetable.json and timetable.xlsx")


if __name__ == "__main__":
    main()

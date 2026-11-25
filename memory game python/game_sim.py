"""
Reference model of the gantry memory game - a tick-by-tick Python port of the
Simulink model built by build_gantry_model.m:

    Chart   -> the Stateflow chart "GameController"  (same states / names)
    Motion  -> the MATLAB Function block "Motion"     (step/dir generation, homing)
    Plant   -> the MATLAB Function block "VirtualGantry" (sim mode only)

Use it to check the game logic on a laptop before touching hardware:

    python game_sim.py                       # random layout, prints a log
    python game_sim.py --layout 0 1 2 0 2 1  # a specific layout (marker ID per slot)
    python -m unittest test_game_sim         # full test set

Game rule (as agreed by the team):
    1. Go to the first not-yet-shot card counted from the gantry origin.
       Read it and ALWAYS shoot it.
    2. Read the following not-yet-shot cards one by one until one has the same
       ArUco ID, then shoot that one.
    3. Repeat from 1 until all cards are shot.
"""
from __future__ import annotations

import argparse
import random
from dataclasses import dataclass, field


# --------------------------------------------------------------------------
# Parameters - keep in step with matlab/gantry_params.m
# --------------------------------------------------------------------------
@dataclass
class Params:
    Ts: float = 0.001             # base sample time [s] (1 kHz)
    STEPS_PER_MM: float = 5.0     # MEASURE THIS on your gantry
    TRAVEL_MM: float = 600.0
    N_SLOTS: int = 6
    SLOT0_MM: float = 50.0        # centre of slot 1 from home switch [mm]
    PITCH_MM: float = 100.0       # slot spacing [mm]
    LASER_OFFSET_MM: float = 0.0  # laser spot x minus camera centre x [mm]
    STEP_HALF_TICKS: int = 1      # ticks per half step period -> 500 steps/s
    SETTLE_S: float = 0.3         # wait after stopping before reading
    READ_TIMEOUT_S: float = 1.0   # per read attempt
    MAX_READ_TRIES: int = 3
    FIRE_S: float = 1.0           # laser on time per target
    HOMING_MAX_MM: float = 700.0  # fault if no end switch within this travel
    DIR_POS_LEVEL: bool = True    # DIR pin level that moves AWAY from home
    ENDSW_ACTIVE_LOW: bool = True # end switch input reads 0 when pressed
    ENABLE_ACTIVE_LOW: bool = True

    def cam_steps(self, slot: int) -> int:
        """Steps to put the camera centre over slot (1-based)."""
        return round((self.SLOT0_MM + (slot - 1) * self.PITCH_MM) * self.STEPS_PER_MM)

    def laser_steps(self, slot: int) -> int:
        """Steps to put the laser spot over slot (1-based)."""
        return round((self.SLOT0_MM + (slot - 1) * self.PITCH_MM - self.LASER_OFFSET_MM)
                     * self.STEPS_PER_MM)

    @property
    def max_steps(self) -> int:
        return round(self.TRAVEL_MM * self.STEPS_PER_MM)


# State codes - same numbers as the chart output "state_code"
STATES = ["Idle", "Homing", "SelectFirst", "MoveCam", "Settle", "Read", "Decide",
          "Aim", "Fire", "AfterFire", "NextCandidate", "ReadFail", "Done", "Fault"]
CODE = {s: i for i, s in enumerate(STATES)}


def first_undone(done: list[bool]) -> int:
    for i, d in enumerate(done):
        if not d:
            return i + 1
    return 0


def next_undone(done: list[bool], after: int) -> int:
    for i in range(after, len(done)):   # slots after+1 .. N (1-based)
        if not done[i]:
            return i + 1
    return 0


# --------------------------------------------------------------------------
# Stateflow chart "GameController"
# --------------------------------------------------------------------------
class Chart:
    def __init__(self, p: Params):
        self.p = p
        self.state = "Idle"
        self.t = 0                      # ticks since entering current state
        # outputs
        self.target_steps = 0
        self.home_cmd = False
        self.laser_on = False
        self.err_count = 0
        self.shots = 0
        # locals
        self.done = [False] * p.N_SLOTS
        self.phase = 1                  # 1 = first card of a round, 2 = searching for its match
        self.slot = 0
        self.ref_id = -1
        self.read_id = -1
        self.tries = 0
        self.last_seq = 0
        self._enter("Idle", None)

    def after(self, seconds: float) -> bool:
        return self.t * self.p.Ts >= seconds - 1e-9

    def _enter(self, s: str, u):
        self.state, self.t = s, 0
        p = self.p
        if s == "Idle":
            self.laser_on = False
            self.home_cmd = False
        elif s == "Homing":
            self.home_cmd = True
            self.laser_on = False
            self.done = [False] * p.N_SLOTS
            self.err_count = 0
            self.shots = 0
            self.phase = 1
        elif s == "SelectFirst":
            self.phase = 1
            self.slot = first_undone(self.done)
        elif s == "MoveCam":
            self.target_steps = p.cam_steps(self.slot)
        elif s == "Settle":
            self.tries = 0
        elif s == "Read":
            self.last_seq = u["vis_seq"]
        elif s == "Aim":
            self.target_steps = p.laser_steps(self.slot)
        elif s == "Fire":
            self.laser_on = True
        elif s == "NextCandidate":
            self.slot = next_undone(self.done, self.slot)
        elif s == "ReadFail":
            self.err_count += 1
        elif s == "Done":
            self.target_steps = 0
            self.laser_on = False
        elif s == "Fault":
            self.laser_on = False
            self.home_cmd = False

    def step(self, u: dict):
        """u: start, homed, fault, pos_steps, vis_seq, vis_id, vis_valid (all one tick old)."""
        self.t += 1
        s, p = self.state, self.p
        go = None
        if s == "Idle":
            if u["start"]:
                go = "Homing"
        elif s == "Homing":
            if u["fault"]:
                go = "Fault"
            elif u["homed"]:
                self.home_cmd = False
                go = "SelectFirst"
        elif s == "SelectFirst":
            go = "Done" if self.slot == 0 else "MoveCam"
        elif s == "MoveCam":
            if u["pos_steps"] == self.target_steps:
                go = "Settle"
        elif s == "Settle":
            if self.after(p.SETTLE_S):
                go = "Read"
        elif s == "Read":
            if u["vis_seq"] >= self.last_seq + 2 and u["vis_valid"]:
                self.read_id = u["vis_id"]
                go = "Decide"
            elif self.after(p.READ_TIMEOUT_S) and self.tries < p.MAX_READ_TRIES - 1:
                self.tries += 1
                go = "Read"
            elif self.after(p.READ_TIMEOUT_S):
                go = "ReadFail"
        elif s == "Decide":
            if self.phase == 1:
                self.ref_id = self.read_id
                go = "Aim"
            elif self.read_id == self.ref_id:
                go = "Aim"
            else:
                go = "NextCandidate"
        elif s == "Aim":
            if u["pos_steps"] == self.target_steps:
                go = "Fire"
        elif s == "Fire":
            if self.after(p.FIRE_S):
                self.laser_on = False
                self.done[self.slot - 1] = True
                self.shots += 1
                go = "AfterFire"
        elif s == "AfterFire":
            if self.phase == 1:
                self.phase = 2
                go = "NextCandidate"
            else:
                go = "SelectFirst"
        elif s == "NextCandidate":
            if self.slot == 0:
                self.err_count += 1          # first card had no matching partner
                go = "SelectFirst"
            else:
                go = "MoveCam"
        elif s == "ReadFail":
            if self.phase == 1:
                self.done[self.slot - 1] = True   # cannot identify first card: give up on it
                go = "SelectFirst"
            else:
                go = "NextCandidate"              # skip unreadable candidate
        elif s == "Done":
            if not u["start"]:
                go = "Idle"
        # Fault: no way out (power-cycle / restart model)
        if go is not None:
            self._enter(go, u)

    @property
    def state_code(self) -> int:
        return CODE[self.state]


# --------------------------------------------------------------------------
# MATLAB Function block "Motion"
# --------------------------------------------------------------------------
class Motion:
    def __init__(self, p: Params):
        self.p = p
        self.pos = 0
        self.level = False
        self.cnt = 0
        self.dir_sign = 1
        self.homed = False
        self.fault = False
        self.prev_home_cmd = False
        self.homing_steps = 0

    def step(self, target_steps, home_cmd, home_sw_raw):
        p = self.p
        home_sw = (not home_sw_raw) if p.ENDSW_ACTIVE_LOW else bool(home_sw_raw)
        if home_cmd and not self.prev_home_cmd:      # new homing request
            self.homed, self.fault, self.homing_steps = False, False, 0
        self.prev_home_cmd = home_cmd

        want = 0
        homing = home_cmd and not self.homed
        if homing:
            if home_sw:
                self.pos, self.homed = 0, True
            elif self.homing_steps >= round(p.HOMING_MAX_MM * p.STEPS_PER_MM):
                self.fault = True
            else:
                want = -1
        elif not home_cmd:
            tgt = min(max(round(target_steps), 0), p.max_steps)
            if tgt > self.pos:
                want = 1
            elif tgt < self.pos:
                if home_sw:
                    self.pos = 0                       # hit switch early: re-zero
                else:
                    want = -1
        if self.fault:
            want = 0

        if self.level:                                 # finish the high half of a pulse
            self.cnt += 1
            if self.cnt >= p.STEP_HALF_TICKS:
                self.level, self.cnt = False, 0
        elif want != 0:
            if want != self.dir_sign:                  # change DIR while STEP is low, then wait
                self.dir_sign, self.cnt = want, 0
            else:
                self.cnt += 1
                if self.cnt >= p.STEP_HALF_TICKS:
                    self.level, self.cnt = True, 0     # rising edge = one step
                    self.pos += want
                    if homing:
                        self.homing_steps += 1
        else:
            self.cnt = 0

        dir_out = p.DIR_POS_LEVEL if self.dir_sign > 0 else (not p.DIR_POS_LEVEL)
        enable_out = not p.ENABLE_ACTIVE_LOW
        return dict(step=self.level, dir=dir_out, enable=enable_out,
                    pos_steps=self.pos, homed=self.homed, fault=self.fault)


# --------------------------------------------------------------------------
# MATLAB Function block "VirtualGantry" (simulation only)
# --------------------------------------------------------------------------
@dataclass
class Plant:
    p: Params
    layout: list[int]                 # marker ID per slot, -1 = unreadable card
    start_steps: int = 1234           # carriage starts somewhere unknown
    frame_ticks: int = 50             # camera frame every 50 ms (20 fps)
    vis_tol_mm: float = 10.0          # camera reads a card within +-10 mm of centre
    switch_works: bool = True
    actual: int = field(init=False)
    prev_step: bool = field(default=False, init=False)
    prev_laser: bool = field(default=False, init=False)
    tick: int = field(default=0, init=False)
    seq: int = field(default=0, init=False)
    vis_id: int = field(default=-1, init=False)
    vis_valid: bool = field(default=False, init=False)
    hits: list = field(default_factory=list, init=False)       # slot hit at each laser-on
    laser_moving: bool = field(default=False, init=False)       # laser on while carriage moved

    def __post_init__(self):
        self.actual = self.start_steps

    def slot_under(self, x_mm: float) -> int:
        p = self.p
        k = round((x_mm - p.SLOT0_MM) / p.PITCH_MM)
        if 0 <= k < p.N_SLOTS and abs(x_mm - (p.SLOT0_MM + k * p.PITCH_MM)) <= self.vis_tol_mm:
            return k + 1
        return 0

    def step(self, step, dir_, laser):
        p = self.p
        if step and not self.prev_step:
            moved = 1 if dir_ == p.DIR_POS_LEVEL else -1
            self.actual = max(self.actual + moved, -20)   # hard stop just past switch
            if laser:
                self.laser_moving = True
        self.prev_step = step
        if laser and not self.prev_laser:
            laser_mm = self.actual / p.STEPS_PER_MM + p.LASER_OFFSET_MM
            self.hits.append(self.slot_under(laser_mm))
        self.prev_laser = laser

        self.tick += 1
        if self.tick % self.frame_ticks == 0:
            self.seq += 1
            k = self.slot_under(self.actual / p.STEPS_PER_MM)
            if k and self.layout[k - 1] >= 0:
                self.vis_id, self.vis_valid = self.layout[k - 1], True
            else:
                self.vis_id, self.vis_valid = -1, False

        pressed = self.switch_works and self.actual <= 0
        home_sw_raw = (not pressed) if p.ENDSW_ACTIVE_LOW else pressed
        return dict(home_sw_raw=home_sw_raw, vis_seq=self.seq,
                    vis_id=self.vis_id, vis_valid=self.vis_valid)


# --------------------------------------------------------------------------
def expected_hits(layout: list[int]) -> list[int]:
    """The team's rule applied directly to a layout (ground truth for tests)."""
    done = [False] * len(layout)
    order = []
    while not all(done):
        i = done.index(False)
        done[i] = True
        order.append(i + 1)
        if layout[i] < 0:
            order.pop()                       # unreadable first card is skipped, not shot
            continue
        for j in range(i + 1, len(layout)):
            if not done[j] and layout[j] == layout[i]:
                done[j] = True
                order.append(j + 1)
                break
    return order


def run(layout, p: Params | None = None, max_s: float = 600.0, verbose=False, **plant_kw):
    p = p or Params()
    chart, motion, plant = Chart(p), Motion(p), Plant(p, list(layout), **plant_kw)
    m_out = dict(step=False, dir=True, enable=False, pos_steps=0, homed=False, fault=False)
    # initial end-switch value = "released" level (matches Unit Delay initial condition in Simulink)
    pl_out = dict(home_sw_raw=p.ENDSW_ACTIVE_LOW, vis_seq=0, vis_id=-1, vis_valid=False)
    last_state = None
    for k in range(int(max_s / p.Ts)):
        chart.step(dict(start=True, homed=m_out["homed"], fault=m_out["fault"],
                        pos_steps=m_out["pos_steps"], **{x: pl_out[x] for x in
                        ("vis_seq", "vis_id", "vis_valid")}))
        m_new = motion.step(chart.target_steps, chart.home_cmd, pl_out["home_sw_raw"])
        pl_out = plant.step(m_new["step"], m_new["dir"], chart.laser_on)
        m_out = m_new
        if verbose and chart.state != last_state:
            extra = f" slot={chart.slot}" if chart.state in ("MoveCam", "Aim", "Fire") else ""
            if chart.state == "Decide":
                extra = f" read_id={chart.read_id} ref_id={chart.ref_id}"
            print(f"{k * p.Ts:8.3f}s  {chart.state:<13}{extra}")
            last_state = chart.state
        if chart.state in ("Done", "Fault") and m_out["pos_steps"] == chart.target_steps:
            break
    return dict(state=chart.state, hits=plant.hits, shots=chart.shots,
                err_count=chart.err_count, time_s=k * p.Ts,
                laser_moving=plant.laser_moving, final_actual=plant.actual)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--layout", type=int, nargs=6, help="marker ID in slots 1..6 (-1 = unreadable)")
    ap.add_argument("--seed", type=int)
    a = ap.parse_args()
    layout = a.layout
    if layout is None:
        layout = [0, 0, 1, 1, 2, 2]
        random.Random(a.seed).shuffle(layout)
    print("layout (slot 1..6):", layout)
    r = run(layout, verbose=True)
    print(f"\nend state {r['state']}, laser hit slots {r['hits']} "
          f"(expected {expected_hits(layout)}), errors {r['err_count']}, time {r['time_s']:.1f}s")


if __name__ == "__main__":
    main()

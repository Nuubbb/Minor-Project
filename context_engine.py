"""
context_engine.py
--------------------------------------------------------------------------------
Context-Aware Threat Assessment Engine for the Real-Time Surveillance System.

Instead of raising an alarm on ANY single detection, this engine COMBINES every
signal (violence, weapons, number of people, time of day, dwell time) and decides
an appropriate RESPONSE LEVEL. This is the core false-alarm-reduction logic.

RESPONSE TIERS (severity, low -> high):
    IGNORE  - do nothing
    LOG     - silently record to the database (no popup, no sound)
    NOTIFY  - desktop notification + log (operator should look)
    ALARM   - siren + notification + log (immediate threat)

DESIGN PRINCIPLES (these are the defense talking points):
    1. Persistence  - violence must be SUSTAINED, not a 1-frame blip
                      -> a playful pat while laughing never alarms.
    2. Combination  - a lone signal is weak; combined signals escalate
                      -> a lone knife is logged; a knife WITH violence alarms.
    3. Context      - the same signal means different things by time/situation
                      -> a knife in a shop by day = normal; after hours = suspicious.
    4. Cooldown     - the same event is not repeated
                      -> a knife sitting in a shop does NOT spam 1000 notifications.
    5. Confidence   - low-confidence detections are ignored
                      -> blurry "maybe a gun" doesn't trigger anything.
"""
import time

# response tiers as ordered numbers (higher = more severe)
IGNORE, LOG, NOTIFY, ALARM = 0, 1, 2, 3
TIER_NAME = {IGNORE: "IGNORE", LOG: "LOG", NOTIFY: "NOTIFY", ALARM: "ALARM"}


class ThreatAssessor:
    def __init__(self,
                 violence_threshold=0.75,   # confidence for a frame to count as violent
                 violence_streak=4,         # consecutive violent frames before it's "real"
                 weapon_conf=0.60,          # ignore weapon detections below this confidence
                 closing_hour=17,           # after-hours starts (5 PM)
                 dwell_seconds=15,          # loitering threshold
                 log_cooldown=30,           # seconds between repeated LOGs of same type
                 notify_cooldown=20):       # seconds between repeated NOTIFYs of same type
        self.violence_threshold = violence_threshold
        self.violence_streak_needed = violence_streak
        self.weapon_conf = weapon_conf
        self.closing_hour = closing_hour
        self.dwell_seconds = dwell_seconds
        self.log_cooldown = log_cooldown
        self.notify_cooldown = notify_cooldown

        self._violent_streak = 0     # how many frames in a row have been violent
        self._track_start = {}       # person_id -> first-seen time (loitering)
        self._last_fire = {}         # alert_type -> last time we acted on it

    # ---------- helper rules ----------
    def _sustained_violence(self, prob):
        """PRINCIPLE 1: True only if violence PERSISTED (kills playful 1-frame blips)."""
        if prob >= self.violence_threshold:
            self._violent_streak += 1
        else:
            self._violent_streak = 0
        return self._violent_streak >= self.violence_streak_needed

    def _strong_weapons(self, weapons):
        """PRINCIPLE 5: keep only confident weapon detections."""
        return [name for (name, conf) in weapons if conf >= self.weapon_conf]

    def _loitering(self, track_ids, now, after_hours):
        """A tracked person staying longer than dwell_seconds (after hours only)."""
        if not after_hours:
            self._track_start.clear()
            return False
        for pid in track_ids:
            self._track_start.setdefault(pid, now)
            if now - self._track_start[pid] > self.dwell_seconds:
                return True
        return False

    def _cooldown_ok(self, alert_type, now, cooldown):
        """PRINCIPLE 4: True only if enough time passed since we last acted on this type."""
        if now - self._last_fire.get(alert_type, -1e9) >= cooldown:
            self._last_fire[alert_type] = now
            return True
        return False

    # ---------- main decision ----------
    def assess(self, violence_prob=0.0, weapons=None, person_count=0,
               track_ids=None, current_hour=None, now=None):
        """
        Combine all signals into ONE response decision.
        Returns: (tier, alert_type, message, confidence)
        """
        weapons = weapons or []
        track_ids = track_ids or []
        now = time.time() if now is None else now
        if current_hour is None:
            current_hour = time.localtime(now).tm_hour
        after_hours = current_hour >= self.closing_hour

        sustained = self._sustained_violence(violence_prob)
        guns_knives = self._strong_weapons(weapons)
        has_weapon = len(guns_knives) > 0

        # ================= ESCALATION MATRIX (first match wins, high -> low) =================

        # 1) weapon + sustained violence -> clearest real threat
        if has_weapon and sustained:
            return ALARM, "weapon+violence", f"ALARM: {guns_knives[0]} with violence!", violence_prob

        # 2) sustained violence alone -> alarm
        if sustained:
            return ALARM, "violence", "ALARM: Violence detected!", violence_prob

        # 3) weapon among several people (PRINCIPLE 2: combined) -> notify
        if has_weapon and person_count >= 2:
            if self._cooldown_ok("weapon-near-people", now, self.notify_cooldown):
                return NOTIFY, "weapon-near-people", f"NOTIFY: {guns_knives[0]} near people", 0.7
            return IGNORE, "", "", 0.0

        # 4) crowd after hours (PRINCIPLE 3: context) -> notify
        if after_hours and person_count >= 3:
            if self._cooldown_ok("after-hours-crowd", now, self.notify_cooldown):
                return NOTIFY, "after-hours-crowd", "NOTIFY: Crowd after working hours", 0.6
            return IGNORE, "", "", 0.0

        # 5) loitering after hours -> notify
        if self._loitering(track_ids, now, after_hours):
            if self._cooldown_ok("loitering", now, self.notify_cooldown):
                return NOTIFY, "loitering", "NOTIFY: Loitering after hours", 0.5
            return IGNORE, "", "", 0.0

        # 6) LONE weapon (e.g. knife in a shop) -> SILENT LOG ONLY, with cooldown (PRINCIPLE 4)
        if has_weapon:
            if self._cooldown_ok("weapon-seen", now, self.log_cooldown):
                return LOG, "weapon-seen", f"logged: {guns_knives[0]} seen (monitoring)", 0.4
            return IGNORE, "", "", 0.0

        # nothing significant
        return IGNORE, "", "", 0.0
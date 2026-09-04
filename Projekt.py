from __future__ import annotations
import json
import random
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from tkinter import Tk, Frame, Label, Button, Listbox, StringVar, END, BOTH, LEFT, RIGHT, X, W
from tkinter import messagebox

APP_TITLE = "MotoGP Telemetry Simulator"
DATA_FILE = Path("telemetry_sessions.json")

class Bike:
    """Klasa bazowa opisująca motocykl"""

    def __init__(self, name: str, horsepower: int, weight_kg: float, max_rpm: int, redline_rpm: int) -> None:
        self._name = name                   #nazwa motocykla
        self._horsepower = horsepower       #liczba koni mechanicznych
        self._weight_kg = weight_kg         #masa jaką posiada motocykl
        self._max_rpm = max_rpm             #maksymalna liczba obrotów na minute
        self._redline_rpm = redline_rpm     #limit obrotów nie uszkadzających silnika

    @property
    def name(self) -> str:
        return self._name

    @property
    def horsepower(self) -> int:
        return self._horsepower

    @property
    def weight_kg(self) -> float:
        return self._weight_kg

    @property
    def max_rpm(self) -> int:
        return self._max_rpm

    @property
    def redline_rpm(self) -> int:
        return self._redline_rpm

    def __str__(self) -> str:
        return f"{self._name} ({self._horsepower} HP, {self._weight_kg} kg)"


class ApriliaRSGP26(Bike):
    """Konkretny motocykl który zostanie użyty w symulacji"""

    def __init__(self) -> None:
        super().__init__(
            name="Aprilia RS-GP26",
            horsepower=295,
            weight_kg=157.0,
            max_rpm=18500,
            redline_rpm=18000,
        )

    def launch_character(self) -> float:
        #mnożnik przyspieszenia
        return 1.08


class Track:
    """Klasa opisująca tor wyścigowy"""

    def __init__(self, name: str, length_km: float, straight_m: int, right_corners: int, left_corners: int, sectors: int) -> None:
        self._name = name
        self._length_km = length_km
        self._straight_m = straight_m
        self._right_corners = right_corners
        self._left_corners = left_corners
        self._sectors = sectors

    @property
    def name(self) -> str:
        return self._name

    @property
    def length_km(self) -> float:
        return self._length_km

    @property
    def sectors(self) -> int:
        return self._sectors

    def sector_name(self, sector_index: int) -> str:
        return f"Sector {sector_index + 1}"

    def __str__(self) -> str:
        return (
            f"{self._name} | {self._length_km:.2f} km | "
            f"Straights: {self._straight_m} m | Corners R/L: {self._right_corners}/{self._left_corners}"
        )


@dataclass
class TelemetrySnapshot:
    timestamp: str          #aktualny czas
    lap: int                #okrążenie
    sector: str             #sektor
    speed_kph: float        #prędkość w kilometrach na godzine
    rpm: int                #liczba obrotów silnika
    gear: int               #aktualny bieg na którym jest motocykl
    lean_angle_deg: float   #aktualne przechylenie motocykla
    throttle_pct: int       #pedał gazu
    brake_pct: int          #pedał hamulca
    fuel_l: float           #stan paliwa
    lap_time_s: float       #czas okrążenia


class TelemetrySession:
    def __init__(self, bike: Bike, track: Track) -> None:
        self.bike = bike
        self.track = track
        self.running = False

        #stan początkowy symulacji
        self.lap = 1
        self.sector_index = 0
        self.speed_kph = 0.0
        self.rpm = 12000
        self.gear = 1
        self.lean_angle_deg = 0.0
        self.throttle_pct = 0
        self.brake_pct = 0
        self.fuel_l = 20.0
        self.lap_time_s = 0.0

        #historia pomiarów do wyświetlania i zapisu
        self.lap_history: list[TelemetrySnapshot] = []
        self._last_tick = time.time()

    def start(self) -> None:
        self.running = True
        self._last_tick = time.time()

    def pause(self) -> None:
        self.running = False

    def reset(self) -> None:
        self.running = False
        self.lap = 1
        self.sector_index = 0
        self.speed_kph = 0.0
        self.rpm = 12000
        self.gear = 1
        self.lean_angle_deg = 0.0
        self.throttle_pct = 0
        self.brake_pct = 0
        self.fuel_l = 20.0
        self.lap_time_s = 0.0
        self.lap_history.clear()
        self._last_tick = time.time()

    def _track_profile_factor(self) -> float:
        if self.sector_index == 0:
            return 1.35
        if self.sector_index == 1:
            return 0.95
        return 1.10

    def _update_gear(self) -> None:
        if self.speed_kph < 35:
            self.gear = 1
        elif self.speed_kph < 70:
            self.gear = 2
        elif self.speed_kph < 105:
            self.gear = 3
        elif self.speed_kph < 140:
            self.gear = 4
        elif self.speed_kph < 175:
            self.gear = 5
        else:
            self.gear = 6

    def _record_snapshot(self) -> None:
        snapshot = TelemetrySnapshot(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            lap=self.lap,
            sector=self.track.sector_name(self.sector_index),
            speed_kph=round(self.speed_kph, 1),
            rpm=int(self.rpm),
            gear=self.gear,
            lean_angle_deg=round(self.lean_angle_deg, 1),
            throttle_pct=self.throttle_pct,
            brake_pct=self.brake_pct,
            fuel_l=round(self.fuel_l, 2),
            lap_time_s=round(self.lap_time_s, 2),
        )
        self.lap_history.append(snapshot)

    def tick(self) -> TelemetrySnapshot:
        """Wykonuje jeden krok symulacji"""
        if not self.running:
            #jeżeli symulacja jest zatrzymana to zwracamy bieżący stan
            return TelemetrySnapshot(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                lap=self.lap,
                sector=self.track.sector_name(self.sector_index),
                speed_kph=self.speed_kph,
                rpm=self.rpm,
                gear=self.gear,
                lean_angle_deg=self.lean_angle_deg,
                throttle_pct=self.throttle_pct,
                brake_pct=self.brake_pct,
                fuel_l=self.fuel_l,
                lap_time_s=self.lap_time_s,
            )

        now = time.time()
        dt = max(0.10, now - self._last_tick)
        self._last_tick = now

        #na prostej więcej gazu, a na zakrętach więcej hamowania
        if self.sector_index == 0:
            self.throttle_pct = min(100, self.throttle_pct + random.randint(3, 11))
            self.brake_pct = max(0, self.brake_pct - random.randint(0, 4))
        elif self.sector_index == 1:
            self.throttle_pct = max(35, self.throttle_pct + random.randint(-6, 4))
            self.brake_pct = min(45, self.brake_pct + random.randint(2, 11))
        else:
            self.throttle_pct = min(100, self.throttle_pct + random.randint(2, 6))
            self.brake_pct = max(0, self.brake_pct - random.randint(0, 3))

        profile = self._track_profile_factor()
        launch_bonus = getattr(self.bike, "launch_character", lambda: 1.0)()

        #aplikujemy: przyspieszenie & hamowanie & opór powietrza
        acceleration = (self.throttle_pct / 100.0) * 34.0 * profile * launch_bonus
        braking = (self.brake_pct / 100.0) * 42.0
        drag = (self.speed_kph ** 2) * 0.0012
        delta_speed = (acceleration - braking - drag) * dt

        self.speed_kph = max(0.0, min(330.0, self.speed_kph + delta_speed))
        self._update_gear()

        #RPM rośnie wraz z prędkością, ale ma małe losowe wahania
        base_rpm = 10000 + self.speed_kph * 51
        self.rpm = int(min(self.bike.redline_rpm, max(8500, base_rpm + random.randint(-150, 150))))

        #na zakrętach motocyklista bardziej przechyla się wraz z motocyklem
        if self.sector_index == 1:
            self.lean_angle_deg = min(60.0, 35.0 + (self.speed_kph / 10.0) + random.uniform(-2.5, 2.5))
        else:
            self.lean_angle_deg = max(3.0, 28.0 + random.uniform(-1.5, 2.0))

        #przykładowa symulacja zużycia paliwa i czas okrążenia
        self.fuel_l = max(0.0, self.fuel_l - (0.02 + self.throttle_pct / 10000.0) * dt * 10)
        self.lap_time_s += dt

        #przejście do następnego sektora po przekroczeniu pewnego czasu
        sector_duration_threshold = 18.0 + self.sector_index * 4.5
        if self.lap_time_s >= sector_duration_threshold:
            self.sector_index += 1
            if self.sector_index >= self.track.sectors:
                self.sector_index = 0
                self.lap += 1
                self.lap_time_s = 0.0

        self._record_snapshot()
        return self.lap_history[-1]

    def export_dict(self) -> dict:
        #plik symulacji gotowy do zapisu
        return {
            "bike": {
                "name": self.bike.name,
                "horsepower": self.bike.horsepower,
                "weight_kg": self.bike.weight_kg,
            },
            "track": {
                "name": self.track.name,
                "length_km": self.track.length_km,
                "sectors": self.track.sectors,
            },
            "latest": asdict(self.lap_history[-1]) if self.lap_history else None,   #zapis ostatniego pomiaru
            "history": [asdict(item) for item in self.lap_history[-50:]],           #zapis historii
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),               #zapis czasu
        }


class DataManager:
    """Obsługa pliku JSON: zapis, odczyt i usuwanie sesji."""
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    def load_sessions(self) -> list[dict]:
        if not self.file_path.exists():
            return []
        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            #jeśli plik jest uszkodzony albo nie można go odczytać
            return []

    def save_session(self, session_data: dict) -> None:
        sessions = self.load_sessions()
        sessions.append(session_data)
        with self.file_path.open("w", encoding="utf-8") as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)

    def delete_session(self, index: int) -> None:
        sessions = self.load_sessions()
        if 0 <= index < len(sessions):
            sessions.pop(index)
            with self.file_path.open("w", encoding="utf-8") as f:
                json.dump(sessions, f, ensure_ascii=False, indent=2)


# ========================================================== #
#                           GUI                              #
# ========================================================== #

class App(Tk):
    """Główne okno aplikacji"""

    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1200x700")
        self.minsize(980, 620)

        #obiekty programu
        self.data_manager = DataManager(DATA_FILE)
        self.bike = ApriliaRSGP26()
        self.track = Track(
            name="Lusail International Circuit",
            length_km=5.38,         #długość całego toru
            straight_m=1068,        #długość prostej startowej w metrach
            right_corners=10,       #liczba prawych zakrętów
            left_corners=6,         #liczba lewych zakrętów
            sectors=3,              #liczba sektorów czasowych na torze
        )
        self.session = TelemetrySession(self.bike, self.track)

        #kontener na dwa ekrany
        self.container = Frame(self)
        self.container.pack(fill=BOTH, expand=True)

        self.start_screen = StartScreen(self.container, self)
        self.telemetry_screen = TelemetryScreen(self.container, self)

        self.start_screen.grid(row=0, column=0, sticky="nsew")
        self.telemetry_screen.grid(row=0, column=0, sticky="nsew")

        self.show_start()

    def show_start(self) -> None:
        #ekran startowy
        self.start_screen.tkraise()
        self.start_screen.refresh_saved_sessions()

    def show_telemetry(self) -> None:
        #pokazuje ekran telemetrii
        self.telemetry_screen.tkraise()
        self.telemetry_screen.refresh_labels()


class StartScreen(Frame):
    """Pierwszy ekran - opis projektu i lista zapisanych sesji."""

    def __init__(self, parent: Frame, app: App) -> None:
        super().__init__(parent)
        self.app = app

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        Label(self, text="MotoGP Telemetry Simulator", font=("Arial", 22, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(25, 10)
        )

        Label(
            self,
            text="Aprilia RS-GP26 • Lusail International Circuit • telemetry simulation",
            font=("Arial", 11),
        ).grid(row=1, column=0, columnspan=2, pady=(0, 20))

        #lewa ramka - opis projektu
        left = Frame(self, bd=1, relief="solid", padx=16, pady=16)
        left.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")

        #prawa ramka - zapisane sesje
        right = Frame(self, bd=1, relief="solid", padx=16, pady=16)
        right.grid(row=2, column=1, padx=20, pady=10, sticky="nsew")

        Label(left, text="Project setup", font=("Arial", 14, "bold")).pack(anchor=W, pady=(0, 10))
        Label(left, text=f"Bike: {self.app.bike}", wraplength=420, justify=LEFT).pack(anchor=W, pady=4)
        Label(left, text=f"Track: {self.app.track}", wraplength=420, justify=LEFT).pack(anchor=W, pady=4)
        Label(
            left,
            text="To jest prosty symulator wyścigowego motocykla Aprilia RS-GP26 na torze Lusail International Circuit położony w Katarze.",
            wraplength=420,
            justify=LEFT,
        ).pack(anchor=W, pady=(10, 4))

        Button(left, text="Start telemetry", command=self._start_simulation, width=20).pack(anchor=W, pady=(18, 6))

        Label(right, text="Saved sessions", font=("Arial", 14, "bold")).pack(anchor=W, pady=(0, 10))
        self.session_list = Listbox(right, height=16)
        self.session_list.pack(fill=BOTH, expand=True)

        controls = Frame(right)
        controls.pack(fill=X, pady=(10, 0))
        Button(controls, text="Delete selected", command=self._delete_selected).pack(side=LEFT)
        Button(controls, text="Refresh", command=self.refresh_saved_sessions).pack(side=LEFT, padx=8)

    def _start_simulation(self) -> None:
        #nowa sesja zawsze startuje od początku
        self.app.session.reset()
        self.app.show_telemetry()

    def refresh_saved_sessions(self) -> None:
        self.session_list.delete(0, END)
        sessions = self.app.data_manager.load_sessions()
        if not sessions:
            self.session_list.insert(END, "No saved sessions yet")
            return

        for idx, item in enumerate(sessions, start=1):
            latest = item.get("latest") or {}
            label = (
                f"{idx}. {item.get('track', {}).get('name', 'Track')} | "
                f"{item.get('bike', {}).get('name', 'Bike')} | "
                f"Lap {latest.get('lap', '-')}, {latest.get('speed_kph', '-')} kph"
            )
            self.session_list.insert(END, label)

    def _delete_selected(self) -> None:
        selection = self.session_list.curselection()
        if not selection:
            messagebox.showinfo("Delete session", "Select a session first.")
            return

        index = selection[0]
        if self.session_list.get(index) == "No saved sessions yet":
            return

        confirm = messagebox.askyesno("Delete session", "Do you want to delete the selected saved session?")
        if confirm:
            self.app.data_manager.delete_session(index)
            self.refresh_saved_sessions()


class TelemetryScreen(Frame):
    """Drugi ekran - działa symulacja i widać telemetrię."""

    def __init__(self, parent: Frame, app: App) -> None:
        super().__init__(parent)
        self.app = app
        self._job = None

        header = Frame(self)
        header.pack(fill=X, pady=12)

        Label(header, text="Live telemetry", font=("Arial", 20, "bold")).pack(side=LEFT, padx=20)
        Button(header, text="Back", command=self._back).pack(side=RIGHT, padx=20)

        main = Frame(self)
        main.pack(fill=BOTH, expand=True, padx=18, pady=8)

        #lewy panel - aktualne wartości
        self.left_panel = Frame(main, bd=1, relief="solid", padx=16, pady=16)
        self.left_panel.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))

        #prawy panel - logi pomiarów
        self.right_panel = Frame(main, bd=1, relief="solid", padx=16, pady=16, width=480)
        self.right_panel.pack(side=RIGHT, fill=BOTH, expand=True, padx=(10, 0))
        self.right_panel.pack_propagate(False)

        #StringVar łączy dane z tekstem na ekranie
        self.vars = {
            "bike": StringVar(),
            "track": StringVar(),
            "lap": StringVar(),
            "sector": StringVar(),
            "speed": StringVar(),
            "rpm": StringVar(),
            "gear": StringVar(),
            "lean": StringVar(),
            "throttle": StringVar(),
            "brake": StringVar(),
            "fuel": StringVar(),
            "laptime": StringVar(),
        }

        self._build_left()
        self._build_right()
        self.refresh_labels()

    def _build_left(self) -> None:
        Label(self.left_panel, text="Current state", font=("Arial", 14, "bold")).pack(anchor=W, pady=(0, 8))

        #tworzymy pary: opis + wartość
        fields = [
            ("bike", "Bike"),
            ("track", "Track"),
            ("lap", "Lap"),
            ("sector", "Sector"),
            ("speed", "Speed"),
            ("rpm", "RPM"),
            ("gear", "Gear"),
            ("lean", "Lean angle"),
            ("throttle", "Throttle"),
            ("brake", "Brake"),
            ("fuel", "Fuel"),
            ("laptime", "Lap time"),
        ]

        for key, title in fields:
            row = Frame(self.left_panel)
            row.pack(fill=X, pady=2)
            Label(row, text=f"{title}:", width=14, anchor=W).pack(side=LEFT)
            Label(row, textvariable=self.vars[key], anchor=W).pack(side=LEFT)

        actions = Frame(self.left_panel)
        actions.pack(fill=X, pady=(16, 0))
        Button(actions, text="Start", command=self.start).pack(side=LEFT)
        Button(actions, text="Pause", command=self.pause).pack(side=LEFT, padx=8)
        Button(actions, text="Reset", command=self.reset).pack(side=LEFT)
        Button(actions, text="Save session", command=self.save_session).pack(side=LEFT, padx=8)

        Label(
            self.left_panel,
            text="The values below are generated with simplified rules to imitate telemetry on Lusail.",
            wraplength=380,
            justify=LEFT,
        ).pack(anchor=W, pady=(14, 0))

    def _build_right(self) -> None:
        Label(self.right_panel, text="Latest laps / sectors", font=("Arial", 14, "bold")).pack(anchor=W, pady=(0, 8))
        self.log = Listbox(self.right_panel)
        self.log.pack(fill=BOTH, expand=True)

    def refresh_labels(self) -> None:
        #przepisywanie aktualnego stanu do GUI
        s = self.app.session
        self.vars["bike"].set(s.bike.name)
        self.vars["track"].set(s.track.name)
        self.vars["lap"].set(str(s.lap))
        self.vars["sector"].set(s.track.sector_name(s.sector_index))
        self.vars["speed"].set(f"{s.speed_kph:.1f} kph")
        self.vars["rpm"].set(f"{s.rpm}")
        self.vars["gear"].set(str(s.gear))
        self.vars["lean"].set(f"{s.lean_angle_deg:.1f}°")
        self.vars["throttle"].set(f"{s.throttle_pct}%")
        self.vars["brake"].set(f"{s.brake_pct}%")
        self.vars["fuel"].set(f"{s.fuel_l:.2f} L")
        self.vars["laptime"].set(f"{s.lap_time_s:.2f} s")

        self.log.delete(0, END)
        for item in s.lap_history[-20:]:
            self.log.insert(
                END,
                f"{item.timestamp} | Lap {item.lap} | {item.sector} | {item.speed_kph:.1f} kph | {item.rpm} RPM | G{item.gear}",
            )

    def _tick_loop(self) -> None:
        #jeden krok symulacji + odświeżenie GUI
        snapshot = self.app.session.tick()
        self.refresh_labels()
        self.log.insert(
            END,
            f"{snapshot.timestamp} | Lap {snapshot.lap} | {snapshot.sector} | {snapshot.speed_kph:.1f} kph | {snapshot.rpm} RPM | G{snapshot.gear}",
        )
        self.log.yview_moveto(1)
        self._job = self.after(1000, self._tick_loop)

    def start(self) -> None:
        if self.app.session.running:
            return
        self.app.session.start()
        self._tick_loop()

    def pause(self) -> None:
        self.app.session.pause()
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
        self.refresh_labels()

    def reset(self) -> None:
        self.pause()
        self.app.session.reset()
        self.log.delete(0, END)
        self.refresh_labels()

    def save_session(self) -> None:
        data = self.app.session.export_dict()
        self.app.data_manager.save_session(data)
        messagebox.showinfo("Saved", "Telemetry session saved to JSON file.")
        self.app.start_screen.refresh_saved_sessions()

    def _back(self) -> None:
        self.pause()
        self.app.show_start()

if __name__ == "__main__":
    app = App()
    app.mainloop()
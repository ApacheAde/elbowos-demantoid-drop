#!/usr/bin/env python3
"""Demantoid Drop — neon plinko arcade for ElbowOS."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys

import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "DEMANTOID DROP"
HANDLE = "x.com/ElbowOS"

VOID = (6, 18, 22)
TEAL = (12, 48, 52)
PINE = (20, 72, 64)
LIME = (120, 255, 90)
EMERALD = (40, 210, 120)
GOLD = (255, 210, 70)
CREAM = (240, 255, 230)
MAG = (255, 70, 150)
CYAN = (70, 230, 255)
SLOT_PTS = (50, 100, 250, 500, 250, 100, 50)
SLOT_COLS = (CYAN, EMERALD, GOLD, MAG, GOLD, EMERALD, CYAN)


class Peg:
    def __init__(self, x: float, y: float):
        self.x, self.y = x, y
        self.r = 12
        self.flash = 0.0


class Gem:
    def __init__(self, x: float, tint: tuple[int, int, int]):
        self.x, self.y = x, 250.0
        self.vx = random.uniform(-40, 40)
        self.vy = 40.0
        self.r = 18
        self.tint = tint
        self.alive = True
        self.spin = random.uniform(0, 6.28)


class Game:
    def __init__(self, record: bool):
        self.record = record
        self.surf = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.Font(None, 78)
        self.font_md = pygame.font.Font(None, 50)
        self.font_sm = pygame.font.Font(None, 36)
        self.hopper_x = W * 0.5
        self.hopper_v = 0.0
        self.pegs: list[Peg] = []
        self.gems: list[Gem] = []
        self.sparks: list[list[float]] = []
        self.pops: list[tuple[str, float, float, float]] = []
        self.score = 0
        self.combo = 0
        self.best = 0
        self.drops = 0
        self.t = 0.0
        self.cool = 0.0
        self.auto_dir = 1.0
        self.running = True
        self.screen = None
        self.build_pegs()
        if not record:
            self.screen = pygame.display.set_mode((W, H))
            pygame.display.set_caption(TITLE)

    def build_pegs(self):
        top, bot = 360, 1460
        rows = 9
        for i in range(rows):
            y = top + i * (bot - top) / (rows - 1)
            n = 5 + (i % 2)
            span = 720
            for j in range(n):
                x = W * 0.5 - span / 2 + (j + 0.5) * (span / n)
                if i % 2:
                    x += 36
                self.pegs.append(Peg(x, y))

    def drop(self):
        if self.cool > 0:
            return
        tint = random.choice((LIME, EMERALD, GOLD, CYAN, MAG))
        self.gems.append(Gem(self.hopper_x + random.uniform(-8, 8), tint))
        self.drops += 1
        self.cool = 0.55
        for _ in range(8):
            a = random.uniform(0, 6.28)
            self.sparks.append(
                [self.hopper_x, 236, math.cos(a) * 180, math.sin(a) * 180, 0.28, *GOLD]
            )

    def slot_index(self, x: float) -> int:
        left, right = 120.0, W - 120.0
        t = max(0.0, min(0.999, (x - left) / (right - left)))
        return int(t * 7)

    def land(self, g: Gem):
        idx = self.slot_index(g.x)
        pts = SLOT_PTS[idx]
        if pts >= 250:
            self.combo += 1
        else:
            self.combo = max(0, self.combo - 1) if pts == 50 else self.combo
        self.best = max(self.best, self.combo)
        gained = pts * (1 + self.combo // 3)
        self.score += gained
        tag = "JACK" if pts == 500 else ("RICH" if pts == 250 else f"+{gained}")
        self.pops.append((tag, g.x, 1580, 0.8))
        col = SLOT_COLS[idx]
        for _ in range(16):
            a = random.uniform(0, 6.28)
            self.sparks.append([g.x, 1560, math.cos(a) * 320, math.sin(a) * 220, 0.45, *col])
        g.alive = False

    def autoplay(self):
        target = W * 0.5 + math.sin(self.t * 1.55) * 380 + math.sin(self.t * 0.6) * 90
        err = target - self.hopper_x
        self.hopper_v = max(-640, min(640, err * 4.0))
        if self.cool <= 0:
            self.drop()

    def update(self, dt: float):
        self.t += dt
        self.cool = max(0.0, self.cool - dt)
        if self.record:
            self.autoplay()
        else:
            keys = pygame.key.get_pressed()
            ax = 0.0
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                ax -= 1800
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                ax += 1800
            self.hopper_v += ax * dt
            self.hopper_v *= 0.86
        self.hopper_x += self.hopper_v * dt
        self.hopper_x = max(160.0, min(W - 160.0, self.hopper_x))
        for g in self.gems:
            if not g.alive:
                continue
            g.vy += 1400 * dt
            g.vx *= 0.992
            g.x += g.vx * dt
            g.y += g.vy * dt
            g.spin += dt * 8
            if g.x < 130:
                g.x, g.vx = 130, abs(g.vx) * 0.55
            if g.x > W - 130:
                g.x, g.vx = W - 130, -abs(g.vx) * 0.55
            for p in self.pegs:
                dx, dy = g.x - p.x, g.y - p.y
                dist = math.hypot(dx, dy)
                min_d = g.r + p.r
                if dist < min_d and dist > 0.1:
                    nx, ny = dx / dist, dy / dist
                    overlap = min_d - dist + 1.0
                    g.x += nx * overlap
                    g.y += ny * overlap
                    vn = g.vx * nx + g.vy * ny
                    if vn < 0:
                        g.vx -= 1.25 * vn * nx
                        g.vy -= 1.25 * vn * ny
                    g.vx += random.uniform(-90, 90)
                    g.vy = max(140.0, g.vy * 0.55 + 90)
                    p.flash = 0.22
            if g.y > 1568:
                self.land(g)
        self.gems = [g for g in self.gems if g.alive and g.y < H + 40]
        for p in self.pegs:
            p.flash = max(0.0, p.flash - dt)
        nxt = []
        for sp in self.sparks:
            sp[0] += sp[2] * dt
            sp[1] += sp[3] * dt
            sp[4] -= dt
            if sp[4] > 0:
                nxt.append(sp)
        self.sparks = nxt
        self.pops = [(a, x, y - 50 * dt, life - dt) for a, x, y, life in self.pops if life - dt > 0]

    def draw(self, s: pygame.Surface):
        s.fill(VOID)
        pygame.draw.rect(s, TEAL, (0, 0, 90, H))
        pygame.draw.rect(s, TEAL, (W - 90, 0, 90, H))
        pygame.draw.rect(s, EMERALD, (86, 0, 8, H))
        pygame.draw.rect(s, LIME, (W - 94, 0, 8, H))
        rng = random.Random(3)
        for i in range(36):
            mx = rng.randint(110, W - 110)
            my = (rng.randint(0, H) + int(self.t * (12 + i % 16))) % H
            pygame.draw.circle(s, PINE, (mx, my), 2 + i % 3)
        hx = int(self.hopper_x)
        pygame.draw.polygon(s, GOLD, [(hx - 54, 210), (hx + 54, 210), (hx + 28, 248), (hx - 28, 248)])
        pygame.draw.polygon(s, LIME, [(hx - 40, 214), (hx + 40, 214), (hx + 20, 242), (hx - 20, 242)])
        pygame.draw.circle(s, CREAM, (hx, 226), 7)
        for p in self.pegs:
            col = GOLD if p.flash > 0 else EMERALD
            pygame.draw.circle(s, col, (int(p.x), int(p.y)), p.r)
            pygame.draw.circle(s, CREAM, (int(p.x) - 3, int(p.y) - 3), 4)
        left, right = 120, W - 120
        sw = (right - left) / 7
        for i, pts in enumerate(SLOT_PTS):
            x0 = int(left + i * sw)
            rect = pygame.Rect(x0 + 4, 1576, int(sw) - 8, 92)
            pygame.draw.rect(s, SLOT_COLS[i], rect, border_radius=12)
            pygame.draw.rect(s, CREAM, rect, 2, border_radius=12)
            lab = self.font_sm.render(str(pts), True, VOID)
            s.blit(lab, lab.get_rect(center=rect.center))
        for g in self.gems:
            pts = []
            for k in range(6):
                a = g.spin + k * math.pi / 3
                pts.append((int(g.x + math.cos(a) * g.r), int(g.y + math.sin(a) * g.r)))
            pygame.draw.polygon(s, g.tint, pts)
            pygame.draw.circle(s, CREAM, (int(g.x - 4), int(g.y - 5)), 4)
        for sp in self.sparks:
            pygame.draw.circle(s, (int(sp[5]), int(sp[6]), int(sp[7])), (int(sp[0]), int(sp[1])), 5)
        title = self.font_lg.render(TITLE, True, LIME)
        s.blit(title, title.get_rect(center=(W // 2, 68)))
        handle = self.font_sm.render(HANDLE, True, GOLD)
        s.blit(handle, handle.get_rect(center=(W // 2, 122)))
        s.blit(self.font_md.render(f"SCORE  {self.score}", True, CREAM), (108, 158))
        s.blit(self.font_md.render(f"STREAK {self.combo}   BEST {self.best}", True, MAG), (108, 206))
        s.blit(self.font_sm.render(f"DROPS  {self.drops}", True, CYAN), (108, 254))
        for tag, x, y, life in self.pops:
            img = self.font_md.render(tag, True, GOLD)
            s.blit(img, img.get_rect(center=(int(x), int(y))))
        hint = self.font_sm.render("A / D  steer hopper    SPACE  drop gem", True, (160, 210, 180))
        s.blit(hint, hint.get_rect(center=(W // 2, H - 44)))

    def handle(self, ev):
        if ev.type == pygame.QUIT:
            self.running = False
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.running = False
            elif ev.key in (pygame.K_SPACE, pygame.K_w, pygame.K_DOWN):
                self.drop()
            elif ev.key == pygame.K_r:
                rec = self.record
                self.__init__(rec)

    def play(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                self.handle(ev)
            self.update(dt)
            self.draw(self.surf)
            self.screen.blit(self.surf, (0, 0))
            pygame.display.flip()

    def record_mp4(self, path: str):
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = FPS * 15
        for i in range(frames):
            self.update(1.0 / FPS)
            self.draw(self.surf)
            proc.stdin.write(pygame.image.tostring(self.surf, "RGB"))
            if i % 30 == 0:
                print(f"frame {i}/{frames}", flush=True)
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed: {rc}")
        print("wrote", path)


def main():
    record = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
    if record:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    g = Game(record)
    if record:
        g.record_mp4("/home/workdir/artifacts/demantoid_drop_ElbowOS.mp4")
    else:
        g.play()
    pygame.quit()


if __name__ == "__main__":
    main()

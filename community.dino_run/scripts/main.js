// Dino Run — an endless runner for the BUSY Bar front display (72x16), in
// the spirit of the offline-browser T-rex game.
//
// Controls: START = jump (also starts / retries), OK (hold) = duck,
// BACK = exit. Sound on/off lives in the app's Setup.
//
// Smoothness: nothing on screen is moved by JS. Sky, ground, every obstacle
// and the dino are native .anim layers that the firmware steps once per
// display refresh (16 ms). An obstacle is a 72 px wide animation of itself
// crossing the screen at the current speed; a jump is a section of the dino
// animation; speed-ups switch the ground's section on its loop boundary
// (await_previous_end). JS only starts sections and predicts where
// everything is from the clock, for collisions and the game-over freeze
// (one-frame "still" sections that hold any position).
//
// Generated: build_assets.py injects the sprite/physics data below and
// writes scripts/main.js. Edit main.src.js, not the output.
//
// The bar's JerryScript has no Annex B (no substr etc.): plain ES5 only.

var D = {"DINO_X":3,"GROUND_FRAMES":[210,168,140,120,105],"GROUND_P":210,"HIT_DUCK":[0,0,0,768,960,1022,254,100],"HIT_STAND":[0,224,480,120,248,126,36,108],"JUMP":[1,1,2,2,3,3,4,4,4,5,5,5,6,6,6,6,6,6,6,6,6,6,6,5,5,5,4,4,4,3,3,2,2,1,1,0],"OBST":{"bh":{"frames":{"0":81,"1":65,"2":55,"3":47,"4":41},"hit":[0,0,2,126,0],"top":0,"w":8},"bl":{"frames":{"0":81,"1":65,"2":55,"3":47,"4":41},"hit":[0,0,2,126,0],"top":9,"w":8},"bm":{"frames":{"0":81,"1":65,"2":55,"3":47,"4":41},"hit":[0,0,2,126,0],"top":4,"w":8},"l1":{"frames":{"0":78,"1":63,"2":53,"3":45,"4":40},"hit":[4,4,4,14,4],"top":9,"w":5},"l2":{"frames":{"0":84,"1":68,"2":57,"3":49,"4":43},"hit":[260,260,260,910,260],"top":9,"w":11},"l3":{"frames":{"2":61,"3":52,"4":46},"hit":[16644,16644,16644,58254,16644],"top":9,"w":17},"s1":{"frames":{"0":78,"1":63,"2":53,"3":45,"4":40},"hit":[4,4,14,4],"top":10,"w":5},"s2":{"frames":{"0":84,"1":68,"2":57,"3":49,"4":43},"hit":[260,260,910,260],"top":10,"w":11},"s3":{"frames":{"0":90,"1":73,"2":61,"3":52,"4":46},"hit":[16644,16644,58254,16644],"top":10,"w":17}},"SKY_FRAMES":576,"TIERS":[1.0,1.25,1.5,1.75,2.0]};

var APP = "community.dino_run";
var API = "http://127.0.0.1/api/";

var F = 16.03;               // ms per animation frame (measured on fw 27.14)
var ANCHOR = 14;             // frame 0 shows ~this long after the draw response
var EXPECT = 50;             // ...and ~this long after sending (used until the response)
var OBST_LAG = 64;           // a new obstacle element starts later than a section
                             // switch (it opens the file) and stalls only ever make
                             // it lag further, so lean late (tuned by feel on the bar)
var LEAD = 40;               // send the freeze this early (request -> screen)
var TICK = 10;               // JS loop period
var W = 72;
var DINO_TOP = 6;            // dino sprite top row when standing (8 rows tall)
var PTS_PER_PX = 0.14;       // ~9 points/s at the start, like the original
var TIER_AT = [0, 150, 400, 750, 1200];
var JUMP_N = D.JUMP.length;
var JUMP_MS = JUMP_N * F;
var BUFFER_MS = 110;         // a jump pressed this close before landing still counts
var DEAD_LOCK_MS = 450;      // ignore START this long after dying
var FIRST_SPAWN_MS = 1300;

// Obstacles unlocked per speed tier (repeats = weight).
var POOL = [
  ["s1", "s1", "s1", "s2", "l1", "l1"],
  ["s1", "s2", "s2", "l1", "l2", "s3", "bl", "bh"],
  ["s1", "s2", "s3", "l1", "l2", "l3", "bl", "bm", "bh"],
  ["s2", "s3", "l1", "l2", "l3", "bl", "bm", "bm", "bh"],
  ["s2", "s3", "l2", "l3", "l3", "bl", "bm", "bm", "bh"]
];

// ── Requests ────────────────────────────────────────────────
var inflight = 0;

function request(path, body, method) {
  return fetch(new Request(API + path, {
    method: method || "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  }));
}

// Posts elements now (several may be in flight); cb(tResponse) on success.
function send(els, cb, extra) {
  var body = { application_name: APP, elements: els };
  if (extra) for (var k in extra) body[k] = extra[k];
  inflight++;
  request("display/draw", body).then(function (r) {
    inflight--;
    if (cb) cb(Date.now(), r && r.ok !== false);
  }, function () {
    inflight--;
    if (cb) cb(Date.now(), false);
  });
}

// ── Sound ───────────────────────────────────────────────────
var soundOn = true;
request("apps/settings?app_id=" + APP, undefined, "GET").then(function (r) {
  return r.json();
}).then(function (j) {
  if (j && j.values && j.values.sound === false) soundOn = false;
}).catch(function () {});

function sfx(name) {
  if (!soundOn) return;
  request("audio/play", { application_name: APP, path: "sounds/" + name + ".snd" }).catch(function () {});
}

// ── Elements ────────────────────────────────────────────────
function anim(id, path, section, loop, x, y, z, extra) {
  var e = { id: id, type: "animation", display: "front", align: "top_left",
    path: "anims/" + path + ".anim", section: section, loop: loop, x: x, y: y, z_index: z };
  if (extra) for (var k in extra) e[k] = extra[k];
  return e;
}
function sky() { return anim("sky", "sky", "loop", true, 0, 0, 1); }
function ground(sec, extra) { return anim("gnd", "ground", sec, true, 0, 13, 2, extra); }
function dino(sec, loop, extra) { return anim("dino", "dino", sec, loop, D.DINO_X, 0, 6, extra); }
function obst(o, sec, loop) { return anim(o.id, "obst", sec, loop, 0, 0, 3); }
function gone(el) { el.display_until = "1"; return el; }
function text(id, s, x, y, font, color, align, z) {
  return { id: id, type: "text", display: "front", text: s, font: font, color: color,
    x: x, y: y, align: align || "top_left", z_index: z || 10 };
}
function rect(id, x, y, w, h, color, z) {
  return { id: id, type: "rectangle", display: "front", align: "top_left", x: x, y: y,
    width: w, height: h, fill: "solid", fill_colors: [color], border_width: 0, z_index: z };
}

var GRAY = "#ACACACFF";
var SCORE = "#F0E6B4FF";     // very pale yellow
var DIM = "#6E6E6EFF";
var WHITE = "#E6E6E6FF";
var GOLD = "#E8B830FF";
var GREEN = "#8CCD8CFF";
var ROSE = "#C87A7AFF";      // muted red for GAME OVER
var TITLE_GREEN = "#6EDC6EFF";
var HIDDEN = "#00000000";

function pad5(n) {
  var s = String(n);
  while (s.length < 5) s = "0" + s;
  return s;
}

// ── Persistence ─────────────────────────────────────────────
var hiScore = 0;
try { hiScore = parseInt(localStorage.getItem("hi"), 10) || 0; } catch (e) {}

// ── State ───────────────────────────────────────────────────
var state = "title";         // title | play | dead
var running = true;
var tier, gAnchor, pendingTier, tierSwitchAt, segStart, distBase;
var obstacles, nextSpawnAt, lastType, obstSeq = 0;
var dinoMode, jumpAnchor, duckAnchor, duckHeld = false, jumpBuffered = 0, queued;
var score, shownScore, scoreSentAt, milestone, blinkUntil;
var deadAt, newBest, overlayStep;
var scanFrom = 0;            // collisions are checked from here on
var trash = [];              // elements to delete with the next request
var overlay = {};            // which title / game-over overlay ids exist

function speed() { return D.TIERS[tier]; }

function distanceAt(t) {
  return distBase + speed() * Math.max(0, t - segStart) / F;
}

// Collision masks are row bitmasks (bit i = column i). Each obstacle type
// keeps only its non-empty rows, as absolute screen rows. JerryScript is
// slow (~5 us per simple op), so this is written to allocate nothing.
for (var tn in D.OBST) {
  var ot = D.OBST[tn];
  ot.ys = []; ot.ms = [];
  for (var r = 0; r < ot.hit.length; r++) if (ot.hit[r]) { ot.ys.push(ot.top + r); ot.ms.push(ot.hit[r]); }
}

// Dino at time t -> dTop / dMask / dH / dDuck.
var dTop, dMask, dH, dDuck;
function dinoAt(t) {
  dH = 0; dDuck = false;
  if (dinoMode === "jump") {
    if (t >= jumpAnchor) {
      var jf = Math.floor((t - jumpAnchor) / F);
      if (jf < JUMP_N) dH = D.JUMP[jf];
      else dDuck = queued === "duck";
    }
  } else if (dinoMode === "duck" && t >= duckAnchor) {
    dDuck = true;
  }
  dTop = DINO_TOP - dH;
  dMask = dDuck ? D.HIT_DUCK : D.HIT_STAND;
}

function obstFrame(o, t) { return Math.floor((t - o.anchor) / F); }
function obstX(o, f) { return W - Math.floor(o.s * f); }

function hits(o, x) {
  var dx = x - D.DINO_X;
  if (dx > 10 || dx <= -o.w) return false;
  var ys = o.ys, ms = o.ms;
  for (var j = 0; j < ys.length; j++) {
    var dj = ys[j] - dTop;
    if (dj < 0 || dj > 7) continue;
    if (dMask[dj] & (dx >= 0 ? ms[j] << dx : ms[j] >> -dx)) return true;
  }
  return false;
}

var near = [];               // obstacles close enough to the dino to matter
function collisionAt(t) {
  dinoAt(t);
  for (var i = 0; i < near.length; i++) {
    var o = near[i];
    if (t >= o.anchor && hits(o, obstX(o, obstFrame(o, t)))) return true;
  }
  return false;
}

// ── Game flow ───────────────────────────────────────────────
var titleAt = 0, titleStepN = 0;

function showTitle() {
  state = "title";
  titleAt = Date.now();
  titleStepN = 0;
  var els = [sky(), ground("g0"), dino("idle", true),
    text("msg", "DINO RUN", 43, -1, "small", TITLE_GREEN, "top_mid", 10),
    text("msg2", "PRESS START", 43, 7, "tiny", GRAY, "top_mid", 10)];
  overlay = { msg: true, msg2: true };
  send(els);
}

// Title: the second line alternates "PRESS START" / best score.
function titleStep(t) {
  if (hiScore <= 0 || inflight > 0) return;
  var n = Math.floor((t - titleAt) / 1600) % 2;
  if (n === titleStepN) return;
  titleStepN = n;
  send([text("msg2", n ? "HI " + pad5(hiScore) : "PRESS START", 43, 7, "tiny", GRAY, "top_mid", 10)]);
}

function startGame(now) {
  var els = [];
  if (obstacles) for (var i = 0; i < obstacles.length; i++) els.push(gone(obst(obstacles[i], "s1@0", true)));
  for (i = 0; i < trash.length; i++) els.push(trash[i]);
  trash = [];
  if (overlay.dim) els.push(gone(rect("dim", 0, 0, 72, 7, HIDDEN, 8)));
  if (overlay.msg) els.push(gone(text("msg", " ", 0, 0, "small", HIDDEN, "top_left", 10)));
  if (overlay.msg2) els.push(gone(text("msg2", " ", 0, 0, "tiny", HIDDEN, "top_left", 10)));
  overlay = {};
  els.push(text("sc", "00000", 71, -1, "small", SCORE, "top_right", 10));

  state = "play";
  tier = 0; pendingTier = -1; distBase = 0; segStart = now + 1e9; gAnchor = now + 1e9;
  obstacles = []; lastType = ""; nextSpawnAt = now + FIRST_SPAWN_MS;
  scanFrom = now; score = 0; shownScore = 0; scoreSentAt = now; milestone = 0; blinkUntil = 0;
  newBest = false; jumpBuffered = 0;

  els.push(ground("t0"));
  // The game opens with a hop, like the original.
  dinoMode = "jump"; queued = duckHeld ? "duck" : "run"; jumpAnchor = now + EXPECT;
  els.push(dino("jump", false));
  send(els, function (t) {
    var a = t + ANCHOR;
    gAnchor = a; segStart = a; jumpAnchor = a;
    send([dino(queued, true, { await_previous_end: true })]);
  });
  sfx("jump");
}

function doJump() {
  dinoMode = "jump";
  queued = duckHeld ? "duck" : "run";
  jumpAnchor = Date.now() + EXPECT;       // refined when the request returns
  jumpBuffered = 0;
  send([dino("jump", false)], function (t) {
    jumpAnchor = t + ANCHOR;
    if (state === "play") send([dino(queued, true, { await_previous_end: true })]);
  });
  sfx("jump");
}

function landed(now) { return now >= jumpAnchor + JUMP_MS; }

function setDuck(on) {
  duckHeld = on;
  if (state !== "play") return;
  var now = Date.now();
  if (dinoMode === "jump" && !landed(now)) {
    // In the air: change what plays after landing.
    queued = on ? "duck" : "run";
    send([dino(queued, true, { await_previous_end: true })]);
    return;
  }
  dinoMode = on ? "duck" : "run";
  duckAnchor = now + EXPECT;
  send([dino(dinoMode, true)], function (t) { duckAnchor = t + ANCHOR; });
}

function pick(list) { return list[Math.floor(Math.random() * list.length)]; }

function spawn(now) {
  var pool = POOL[tier], type, tries = 0;
  do {
    type = pick(pool);
    tries++;
  } while ((!D.OBST[type].frames[tier] || (type === lastType && type.charAt(0) === "b")) && tries < 12);
  if (!D.OBST[type].frames[tier]) type = "s1";
  lastType = type;
  var m = D.OBST[type];
  var o = { id: "o" + (obstSeq++ % 1000), type: type, s: speed(), w: m.w, ys: m.ys, ms: m.ms,
    life: m.frames[tier], anchor: now + EXPECT + OBST_LAG };
  obstacles.push(o);
  var els = [obst(o, type + "_" + tier, false)];
  for (var i = 0; i < trash.length; i++) els.push(trash[i]);
  trash = [];
  send(els, function (t) { o.anchor = t + ANCHOR + OBST_LAG; });

  // Next one: the gap always leaves room to land and react (in frames).
  var gap = JUMP_N + 12 + Math.random() * JUMP_N * (tier < 2 ? 1.4 : 1.1);
  if (type === "bm") gap += 8;            // time to get back up after ducking
  nextSpawnAt = now + (m.w / o.s + gap) * F;
}

function scheduleTier(now, k) {
  var n = D.GROUND_FRAMES[tier], loopMs = n * F;
  var b = gAnchor + Math.ceil((now + 150 - gAnchor) / loopMs) * loopMs;
  pendingTier = k;
  tierSwitchAt = b;
  send([ground("t" + k, { await_previous_end: true })]);
}

function applyTier() {
  distBase = distanceAt(tierSwitchAt);
  segStart = tierSwitchAt;
  gAnchor = tierSwitchAt;
  tier = pendingTier;
  pendingTier = -1;
}

function step(now) {
  if (pendingTier >= 0 && now >= tierSwitchAt) applyTier();

  // Score, milestones, speed tiers
  score = Math.floor(distanceAt(now) * PTS_PER_PX);
  var m = Math.floor(score / 100);
  if (m > milestone) {
    milestone = m;
    blinkUntil = now + 900;
    sfx("score");
  }
  if (pendingTier < 0 && tier + 1 < D.TIERS.length && score >= TIER_AT[tier + 1]) scheduleTier(now, tier + 1);

  // Obstacles that have left the screen; the ones near the dino
  var keep = [];
  near.length = 0;
  for (var i = 0; i < obstacles.length; i++) {
    var o = obstacles[i];
    var f = obstFrame(o, now);
    if (f > o.life + 2) { trash.push(gone(obst(o, o.type + "@0", true))); continue; }
    keep.push(o);
    var x = obstX(o, f);
    if (x < D.DINO_X + 11 + 8 * o.s && x > D.DINO_X - o.w - 8 * o.s) near.push(o);
  }
  obstacles = keep;

  // Collisions: every frame since the last check (ticks can run late) up
  // to LEAD ahead, so the freeze is sent to land right on the first contact.
  if (near.length) {
    for (var t = Math.max(scanFrom, now - 6 * F); t <= now + LEAD + F; t += F) {
      if (collisionAt(t)) {
        if (t <= now + LEAD) { die(t); return; }
        break;
      }
    }
  }
  scanFrom = now;

  // Jump pressed just before landing
  if (jumpBuffered && dinoMode === "jump" && now >= jumpAnchor + JUMP_MS - LEAD) doJump();
  if (dinoMode === "jump" && landed(now)) dinoMode = queued;

  if (now >= nextSpawnAt) spawn(now);

  // HUD: score text, throttled; blinks on every 100 like the original
  if (inflight === 0 && now - scoreSentAt >= 100) {
    var blink = now < blinkUntil;
    var shown = blink ? milestone * 100 : score;
    var on = !blink || Math.floor((blinkUntil - now) / 150) % 2 === 1;
    var key = shown * 2 + (on ? 1 : 0);
    if (key !== shownScore) {
      shownScore = key;
      scoreSentAt = now;
      send([text("sc", pad5(shown), 71, -1, "small", on ? SCORE : HIDDEN, "top_right", 10)]);
    } else if (trash.length) {
      send(trash);
      trash = [];
    }
  }
}

function die(t) {
  state = "dead";
  deadAt = Date.now();
  overlayStep = -1;
  dinoAt(t);
  var els = [dino(dDuck ? "deadduck" : "dead" + dH, true)];
  for (var i = 0; i < trash.length; i++) els.push(trash[i]);
  trash = [];
  // Freeze what's on screen; every obstacle element (frozen or not) is
  // deleted when the next game starts.
  for (i = 0; i < obstacles.length; i++) {
    var o = obstacles[i];
    var x = t >= o.anchor ? obstX(o, obstFrame(o, t)) : W;
    if (x > -o.w && x < W) els.push(obst(o, o.type + "@" + x, true));
    trash.push(gone(obst(o, o.type + "@0", true)));
  }
  obstacles = [];
  near.length = 0;
  if (now() >= gAnchor) {
    var n = D.GROUND_FRAMES[tier];
    var gf = ((Math.floor((t - gAnchor) / F) % n) + n) % n;
    els.push(ground("g" + (Math.floor(speed() * gf) % D.GROUND_P)));
  }
  send(els);
  sfx("hit");

  score = Math.floor(distanceAt(t) * PTS_PER_PX);
  if (score > hiScore) {
    newBest = hiScore > 0;
    hiScore = score;
    try { localStorage.setItem("hi", String(hiScore)); } catch (e) {}
  }
}

function now() { return Date.now(); }

// Game-over text: "GAME OVER", then the score / best, alternating.
function deadStep(t) {
  var since = t - deadAt;
  if (since < 350) return;
  var stepN = Math.floor((since - 350) / 1600) % 2;
  if (stepN === overlayStep || inflight > 0) return;
  overlayStep = stepN;
  var els = [];
  if (stepN === 0) {
    els.push(rect("dim", 14, 0, 58, 7, "#000000C8", 8));
    overlay.dim = overlay.msg = true;
    els.push(text("msg", "GAME OVER", 43, -1, "small", ROSE, "top_mid", 10));
    els.push(text("sc", pad5(score), 71, -1, "small", HIDDEN, "top_right", 10));
  } else {
    var line = newBest ? "NEW BEST " + score : score + "  HI " + hiScore;
    els.push(text("msg", line, 43, -1, "small", newBest ? GOLD : GREEN, "top_mid", 10));
  }
  send(els);
}

// ── Loop ────────────────────────────────────────────────────
function tick() {
  if (!running) return;
  var t = Date.now();
  if (state === "play") step(t);
  else if (state === "dead") deadStep(t);
  else if (state === "title") titleStep(t);
  // Check often only while something is close to the dino; otherwise leave
  // the (single) JS thread free for the draw requests.
  setTimeout(tick, state === "play" && (near.length || dinoMode === "jump") ? TICK : 30);
}

// ── Input ───────────────────────────────────────────────────
function quit() {
  if (!running) return;
  running = false;
  request("audio/play", {}, "DELETE").catch(function () {});
  request("display/draw", { application_name: APP }, "DELETE").catch(function () {});
  if (unbind) unbind();
}

var unbind = listen("input", function (e) {
  var t = Date.now();
  if (e.key === "start" && e.action === "press") {
    if (state === "title") startGame(t);
    else if (state === "dead") { if (t - deadAt >= DEAD_LOCK_MS) startGame(t); }
    else if (dinoMode !== "jump" || landed(t)) doJump();
    else if (jumpAnchor + JUMP_MS - t <= BUFFER_MS) jumpBuffered = t;
  } else if (e.key === "ok") {
    if (e.action === "press") setDuck(true);
    else if (e.action === "release") setDuck(false);
  } else if (e.key === "back" && e.action === "press") {
    quit();
  }
});

showTitle();
tick();

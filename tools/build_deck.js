// ARBITER viva deck: title + three five-slide sections, one per member.
// Palette is the product's own interface, so the deck and the live demo read
// as one thing when they are shown side by side.
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("C:/Users/Gautam Lasgotra/.claude/skills/synced/12fa3ec9-e151-4355-8ead-9de287c2351a_b28cba6d-f4a3-4228-b7fd-30ef25e900e3/pptx/scripts/apply_theme.js");

const THEME = {
  name: "ARBITER",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "0F1115", lt1: "FFFFFF",
    dk2: "1D212A", lt2: "E6E9EF",
    accent1: "3DDC97", // mint - the interface accent
    accent2: "5B9DFF", // blue
    accent3: "F0B429", // amber, used for "stopped"
    accent4: "FF6B6B", // red, used for "failed"
    accent5: "8B93A7", // muted
    accent6: "2A2F3A", // hairline
    hlink: "5B9DFF", folHlink: "8B93A7",
  },
};

const BG = THEME.colors.dk1;
const PANEL = THEME.colors.dk2;
const MINT = THEME.colors.accent1;
const BLUE = THEME.colors.accent2;
const AMBER = THEME.colors.accent3;
const RED = THEME.colors.accent4;
const MUTED = THEME.colors.accent5;
const LINE = THEME.colors.accent6;
const FG = THEME.colors.lt2;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";            // 13.3 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.author = "Gautam Lasgotra, Chirag Attri, Aniket Kundal";
pres.title = "ARBITER - Mid-semester Review";

const W = 13.3, H = 7.5, M = 0.7;

// ----------------------------------------------------------------- layouts
pres.defineSlideMaster({
  title: "TITLE",
  background: { color: BG },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 2.25, w: W - 2 * M, h: 1.1,
        fontSize: 54, bold: true, color: THEME.colors.lt1, align: "left" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: M, y: 3.45, w: 9.4, h: 2.6,
        fontSize: 15, color: MUTED, align: "left" }, text: "" } },
  ],
});

pres.defineSlideMaster({
  title: "SECTION",
  background: { color: PANEL },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 3.0, w: W - 2 * M, h: 1.0,
        fontSize: 40, bold: true, color: THEME.colors.lt1, align: "left" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: M, y: 4.05, w: 9.0, h: 1.4,
        fontSize: 16, color: MUTED, align: "left" }, text: "" } },
  ],
});

const contentObjects = [
  { placeholder: { options: { name: "title", type: "title", x: M, y: 0.52, w: W - 2 * M, h: 0.8,
      fontSize: 34, bold: true, color: THEME.colors.lt1, align: "left" }, text: "" } },
  { text: { text: "ARBITER", options: { x: M, y: H - 0.52, w: 2.0, h: 0.3, fontSize: 10,
      color: LINE, align: "left", isTextBox: true, margin: 0 } } },
  { placeholder: { options: { name: "owner", type: "body", x: W - M - 4.2, y: H - 0.52, w: 4.2, h: 0.3,
      fontSize: 10, color: LINE, align: "right" }, text: "" } },
];

pres.defineSlideMaster({ title: "CONTENT", background: { color: BG }, objects: contentObjects });

pres.defineSlideMaster({
  title: "CONTENT_BODY",
  background: { color: BG },
  objects: contentObjects.concat([
    { placeholder: { options: { name: "body", type: "body", x: M, y: 1.5, w: W - 2 * M, h: 4.9,
        fontSize: 16, color: FG, align: "left" }, text: "" } },
  ]),
});

// ------------------------------------------------------------- helpers
const OWNERS = {
  g: "Gautam Lasgotra · 23BCS032",
  c: "Chirag Attri · 23BCS024",
  a: "Aniket Kundal · 23BCS015",
};

function slide(master, section, owner) {
  const s = pres.addSlide({ masterName: master, sectionTitle: section });
  if (owner) s.addText(OWNERS[owner], { placeholder: "owner" });
  return s;
}

/** A tinted card. No edge stripes - a background tint and a shadow instead. */
function card(s, x, y, w, h, opts = {}) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.06,
    fill: { color: opts.fill || PANEL },
    line: { color: opts.line || LINE, width: 1 },
    objectName: opts.name || "card",
    shadow: { type: "outer", color: "000000", blur: 10, offset: 2, angle: 90, opacity: 0.35 },
  });
}

/** A numbered badge in a mint circle - the deck's repeated motif. */
function badge(s, x, y, label, color = MINT, d = 0.42) {
  s.addShape(pres.ShapeType.ellipse, {
    x, y, w: d, h: d, fill: { color }, line: { color }, objectName: "badge-" + label,
  });
  s.addText(String(label), {
    x, y, w: d, h: d, fontSize: 13, bold: true, color: BG,
    align: "center", valign: "middle", isTextBox: true, margin: 0,
  });
}

function kicker(s, text, color = MINT) {
  s.addText(text.toUpperCase(), {
    x: M, y: 1.36, w: W - 2 * M, h: 0.28, fontSize: 11, bold: true, color,
    charSpacing: 1.6, isTextBox: true, margin: 0,
  });
}

function stat(s, x, y, w, value, label, color = MINT) {
  s.addText(value, { x, y, w, h: 0.78, fontSize: 40, bold: true, color,
    align: "left", isTextBox: true, margin: 0 });
  s.addText(label, { x, y: y + 0.76, w, h: 0.5, fontSize: 12, color: MUTED,
    align: "left", isTextBox: true, margin: 0 });
}

// =====================================================================  1
pres.addSection({ title: "Opening" });
{
  const s = pres.addSlide({ masterName: "TITLE", sectionTitle: "Opening" });
  s.addShape(pres.ShapeType.ellipse, { x: M, y: 1.25, w: 0.62, h: 0.62,
    fill: { color: BG }, line: { color: MINT, width: 3 }, objectName: "mark" });
  s.addShape(pres.ShapeType.triangle, { x: M + 0.42, y: 1.14, w: 0.28, h: 0.28,
    fill: { color: MINT }, line: { color: MINT }, rotate: 40, objectName: "mark-head" });

  s.addText("ARBITER", { placeholder: "title" });
  s.addText([
    { text: "Adaptive Multi-Agent System for Iterative Task Generation, Validation and Refinement",
      options: { fontSize: 17, color: FG, breakLine: true } },
    { text: "Does multi-agent refinement still win when the single agent gets the same token budget?",
      options: { fontSize: 14, italic: true, color: MINT, breakLine: true } },
  ], { placeholder: "body" });

  const names = [
    ["Gautam Lasgotra", "23BCS032"],
    ["Chirag Attri", "23BCS024"],
    ["Aniket Kundal", "23BCS015"],
  ];
  names.forEach(([n, e], i) => {
    const x = M + i * 3.1;
    s.addText(n, { x, y: 5.25, w: 2.9, h: 0.3, fontSize: 14, bold: true,
      color: THEME.colors.lt1, isTextBox: true, margin: 0 });
    s.addText(e, { x, y: 5.56, w: 2.9, h: 0.3, fontSize: 12, color: MUTED,
      isTextBox: true, margin: 0 });
  });
  s.addText("Guide: Dr. Sonika Gupta  ·  School of Computer Science & Engineering, SMVDU Katra",
    { x: M, y: 6.45, w: W - 2 * M, h: 0.3, fontSize: 12, color: MUTED, isTextBox: true, margin: 0 });
  s.addNotes("One line: an agent writes a solution, tools test it by actually running it, another agent rewrites it from the failures, repeating under a hard budget. We are measuring whether that still beats a single agent once both get the same token budget.");
}

// ================================================= SECTION A - Gautam
pres.addSection({ title: "1. The system" });
{
  const s = pres.addSlide({ masterName: "SECTION", sectionTitle: "1. The system" });
  badge(s, M, 2.35, "1", MINT, 0.52);
  s.addText("The system", { placeholder: "title" });
  s.addText("What the problem is, how the loop works, and what keeps it bounded", { placeholder: "body" });
  s.addText("Gautam Lasgotra · 23BCS032", { x: M, y: 5.0, w: 6, h: 0.3, fontSize: 13,
    bold: true, color: MINT, isTextBox: true, margin: 0 });
  s.addNotes("I own the orchestration loop, the decision policy, the budget governor, the provider layer, the sandbox, the web interface and the deployment.");
}

{ // ---- 2. the problem
  const s = slide("CONTENT", "1. The system", "g");
  s.addText("Models write code that looks right", { placeholder: "title" });
  kicker(s, "the problem");

  const items = [
    ["1", "It looks correct", "Off-by-one, a missed edge case, an empty input never considered. Plausible, not verified.", MUTED],
    ["2", "It cannot check itself", "Huang et al., ICLR 2024: without feedback from outside the model, self-correction does not help and often degrades.", AMBER],
    ["3", "So give it a fact", "Run the code. Count which tests passed. That number is not an opinion.", MINT],
  ];
  items.forEach(([n, head, body, col], i) => {
    const x = M + i * 4.08;
    card(s, x, 1.95, 3.76, 2.95, { name: "problem-" + n });
    badge(s, x + 0.3, 2.25, n, col);
    s.addText(head, { x: x + 0.3, y: 2.85, w: 3.16, h: 0.4, fontSize: 18, bold: true,
      color: THEME.colors.lt1, isTextBox: true, margin: 0 });
    s.addText(body, { x: x + 0.3, y: 3.3, w: 3.16, h: 1.4, fontSize: 13, color: MUTED,
      isTextBox: true, margin: 0 });
  });

  s.addText([
    { text: "The agent that checks the work is not an LLM. ", options: { bold: true, color: THEME.colors.lt1 } },
    { text: "It is a program that runs the code and reports which tests failed.", options: { color: FG } },
  ], { x: M, y: 5.3, w: W - 2 * M, h: 0.5, fontSize: 17, isTextBox: true, margin: 0 });
  s.addNotes("The obvious fix is to ask the model to review itself. That is exactly what the literature says does not work. Our whole design follows from that: the code validator contains no LLM at all.");
}

{ // ---- 3. the loop
  const s = slide("CONTENT", "1. The system", "g");
  s.addText("How the loop works", { placeholder: "title" });
  kicker(s, "architecture");

  const steps = [
    ["Task", "typed in at runtime", BLUE],
    ["Test designer", "writes executable tests", BLUE],
    ["Generator", "writes a solution", MINT],
    ["python_exec", "RUNS it — no LLM", MINT],
    ["Decision policy", "accept / refine / stop", AMBER],
  ];
  const bw = 2.26, gap = 0.26;
  steps.forEach(([head, sub, col], i) => {
    const x = M + i * (bw + gap);
    card(s, x, 2.1, bw, 1.5, { name: "step-" + i });
    s.addText(head, { x: x + 0.18, y: 2.32, w: bw - 0.36, h: 0.35, fontSize: 14, bold: true,
      color: col, isTextBox: true, margin: 0 });
    s.addText(sub, { x: x + 0.18, y: 2.7, w: bw - 0.36, h: 0.7, fontSize: 11.5, color: MUTED,
      isTextBox: true, margin: 0 });
    if (i < steps.length - 1) {
      s.addText("›", { x: x + bw + 0.02, y: 2.6, w: gap, h: 0.4, fontSize: 20, color: LINE,
        align: "center", isTextBox: true, margin: 0 });
    }
  });

  s.addShape(pres.ShapeType.roundRect, { x: M, y: 3.78, w: 11.9, h: 0.42, rectRadius: 0.1,
    fill: { color: PANEL }, line: { color: LINE, width: 1 }, objectName: "feedback" });
  s.addText("feedback: the names of the tests that failed  ←  loops back to the generator",
    { x: M, y: 3.78, w: 11.9, h: 0.42, fontSize: 12, color: MINT, align: "center",
      valign: "middle", isTextBox: true, margin: 0 });

  s.addText("An agent is a role prompt, one model call, and a typed parse. Agents differ only in their system prompt — repair is told not to trust the previous approach, critic is told to review sceptically.",
    { x: M, y: 4.5, w: 11.9, h: 0.8, fontSize: 14, color: FG, isTextBox: true, margin: 0 });

  stat(s, M, 5.4, 3.0, "~200", "lines in the orchestration core", MINT);
  stat(s, M + 4.08, 5.4, 3.0, "~2,700", "lines of Python in total", BLUE);
  stat(s, M + 8.16, 5.4, 3.3, "0", "LLMs inside the code validator", AMBER);
  s.addNotes("No agent framework. We kept the orchestration explicit because the orchestration is what the project studies — hiding it inside LangGraph or AutoGen would hide the contribution. AutoGen is also in maintenance mode.");
}

{ // ---- 4. one run
  const s = slide("CONTENT", "1. The system", "g");
  s.addText("One real run, step by step", { placeholder: "title" });
  kicker(s, "worked example");

  const rows = [
    ["test_designer", "wrote 4 tests, fixed the name as compare_versions", MUTED, ""],
    ["generator", "first attempt", MUTED, ""],
    ["python_exec", "score = 0.75   ·   3 of 4 tests passed", AMBER, "FAILED"],
    ["llm_critic", "\"passed\"", RED, "FALSE ACCEPT"],
    ["decision policy", "refine", BLUE, ""],
    ["repair", "rewrites it, told not to trust the old approach", MUTED, ""],
    ["python_exec", "score = 1.00", MINT, "ACCEPTED"],
  ];
  rows.forEach(([who, what, col, tag], i) => {
    const y = 1.95 + i * 0.63;
    s.addShape(pres.ShapeType.roundRect, { x: M, y, w: 11.9, h: 0.52, rectRadius: 0.06,
      fill: { color: i % 2 ? BG : PANEL }, line: { color: LINE, width: 1 },
      objectName: "row-" + i });
    s.addText(who, { x: M + 0.22, y, w: 2.5, h: 0.52, fontSize: 13, bold: true, color: col,
      valign: "middle", isTextBox: true, margin: 0 });
    s.addText(what, { x: M + 2.8, y, w: 6.4, h: 0.52, fontSize: 13, color: FG,
      valign: "middle", isTextBox: true, margin: 0 });
    if (tag) {
      s.addText(tag, { x: M + 9.4, y, w: 2.3, h: 0.52, fontSize: 11, bold: true, color: col,
        align: "right", valign: "middle", isTextBox: true, margin: 0 });
    }
  });
  s.addText("The executed tests said FAIL. The LLM critic said PASS. The LLM was wrong — and we log that gap, because measuring it is research question 3.",
    { x: M, y: 6.45, w: 11.9, h: 0.5, fontSize: 14, italic: true, color: MINT,
      isTextBox: true, margin: 0 });
  s.addNotes("Point at rows 3 and 4 during the demo. 0.75 means three of four tests passed — graded, not pass/fail, because the loop needs to tell 'nearly right' from 'stuck'.");
}

{ // ---- 5. bounded
  const s = slide("CONTENT", "1. The system", "g");
  s.addText("It can never run forever", { placeholder: "title" });
  kicker(s, "budget governor");

  const stops = [
    ["accepted", "tests passed"], ["max_iterations", "5 rounds"],
    ["max_llm_calls", "20 calls"], ["max_tokens", "60,000"],
    ["wall_clock", "180 seconds"], ["no_improvement", "2 flat rounds"],
    ["cycle_detected", "identical output"],
  ];
  stops.forEach(([name, sub], i) => {
    const x = M + (i % 4) * 3.05, y = 2.0 + Math.floor(i / 4) * 1.25;
    card(s, x, y, 2.78, 1.0, { name: "stop-" + i });
    s.addText(name, { x: x + 0.2, y: y + 0.14, w: 2.4, h: 0.33, fontSize: 13, bold: true,
      color: i === 0 ? MINT : AMBER, isTextBox: true, margin: 0 });
    s.addText(sub, { x: x + 0.2, y: y + 0.5, w: 2.4, h: 0.33, fontSize: 12, color: MUTED,
      isTextBox: true, margin: 0 });
  });

  card(s, M + 9.15, 3.25, 2.75, 1.0, { name: "mast", fill: BG });
  s.addText("17.1%", { x: M + 9.4, y: 3.35, w: 2.3, h: 0.45, fontSize: 24, bold: true,
    color: RED, isTextBox: true, margin: 0 });
  s.addText("of multi-agent failures are step repetition  ·  MAST, NeurIPS 2025",
    { x: M + 9.4, y: 3.78, w: 2.3, h: 0.42, fontSize: 9.5, color: MUTED,
      isTextBox: true, margin: 0 });

  s.addText("Every stop reason is logged as an enum, so a run that stops can always be explained.",
    { x: M, y: 4.75, w: 11.9, h: 0.4, fontSize: 14, color: FG, isTextBox: true, margin: 0 });
  s.addText("Generated code runs in a separate process with no inherited environment, so it cannot read our API keys — in a temp directory, under a timeout. On the public site a live run needs a token: a public URL that executes model-written Python is a remote shell.",
    { x: M, y: 5.3, w: 11.9, h: 1.0, fontSize: 13, color: MUTED, isTextBox: true, margin: 0 });
  s.addNotes("If asked what stops it looping: seven separate limits, and we can demonstrate it by asking for something impossible.");
}

{ // ---- 6. live
  const s = slide("CONTENT", "1. The system", "g");
  s.addText("Built, deployed and running", { placeholder: "title" });
  kicker(s, "live demonstration");

  card(s, M, 1.95, 11.9, 1.15, { name: "url", fill: PANEL });
  s.addText("arbiter-gules-two.vercel.app", { x: M + 0.35, y: 2.12, w: 7.5, h: 0.5,
    fontSize: 24, bold: true, color: MINT, isTextBox: true, margin: 0 });
  s.addText("Type any task · watch the agents work · every number metered live",
    { x: M + 0.35, y: 2.62, w: 7.5, h: 0.35, fontSize: 13, color: MUTED, isTextBox: true, margin: 0 });

  stat(s, M, 3.4, 2.6, "49", "automated tests, no API key needed", MINT);
  stat(s, M + 3.0, 3.4, 2.6, "5", "conditions, one engine", BLUE);
  stat(s, M + 6.0, 3.4, 2.6, "25", "measured runs so far", BLUE);
  stat(s, M + 9.0, 3.4, 2.9, "3", "demo layers, so it never dies", AMBER);

  const bullets = [
    "FastAPI streaming agent events over Server-Sent Events as they happen",
    "Fluid compute, so one request can stream for a whole run instead of buffering",
    "Offline scripted provider and replay of a stored run as fallbacks",
    "Every push to main redeploys automatically",
  ];
  s.addText(bullets.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < bullets.length - 1 } })),
    { x: M, y: 4.85, w: 11.9, h: 1.5, fontSize: 14, color: FG, paraSpaceAfter: 6,
      isTextBox: true, margin: 0 });
  s.addNotes("Open the link ten minutes early so the first request wakes the server. Use condition C. If a run stalls, say the system stopped itself on a documented limit, then press Offline demo.");
}

// ================================================ SECTION B - Chirag
pres.addSection({ title: "2. The agents" });
{
  const s = pres.addSlide({ masterName: "SECTION", sectionTitle: "2. The agents" });
  badge(s, M, 2.35, "2", BLUE, 0.52);
  s.addText("The agents", { placeholder: "title" });
  s.addText("What an agent actually is, how the roles differ, and why an LLM never has the last word", { placeholder: "body" });
  s.addText("Chirag Attri · 23BCS024", { x: M, y: 5.0, w: 6, h: 0.3, fontSize: 13,
    bold: true, color: BLUE, isTextBox: true, margin: 0 });
  s.addNotes("I own the role library, the prompts, the structured output schemas, the test designer and the LLM critic.");
}

{ // ---- 7. an agent is a function
  const s = slide("CONTENT", "2. The agents", "c");
  s.addText("An agent is a function", { placeholder: "title" });
  kicker(s, "no framework", BLUE);

  card(s, M, 1.95, 7.2, 2.5, { name: "code", fill: PANEL });
  s.addText(
    "def generator(task, router, state, feedback=None):\n" +
    "    prompt = build_prompt(task, feedback)\n" +
    "    resp   = router.call(prompt,\n" +
    "                 schema=SOLUTION_SCHEMA, state=state)\n" +
    "    return Solution.model_validate_json(resp.text)",
    { x: M + 0.3, y: 2.2, w: 6.6, h: 2.0, fontSize: 12.5, fontFace: "Consolas",
      color: MINT, isTextBox: true, margin: 0 });

  const parts = [["A role prompt", MINT], ["One model call", BLUE], ["A typed parse", AMBER]];
  parts.forEach(([t, col], i) => {
    const y = 2.1 + i * 0.82;
    badge(s, M + 7.7, y, String(i + 1), col, 0.38);
    s.addText(t, { x: M + 8.25, y: y - 0.03, w: 3.5, h: 0.45, fontSize: 17, bold: true,
      color: THEME.colors.lt1, valign: "middle", isTextBox: true, margin: 0 });
  });

  s.addText("Agents differ only in their system prompt — same model, same code path. So any measured difference is caused by the prompt and nothing else.",
    { x: M, y: 4.75, w: 11.9, h: 0.6, fontSize: 15, color: FG, isTextBox: true, margin: 0 });
  s.addText("Structured output is enforced: a JSON schema goes with the request and Pydantic parses the reply. If it does not match, parsing raises and the run records the failure instead of passing garbage down the pipeline.",
    { x: M, y: 5.5, w: 11.9, h: 0.8, fontSize: 13, color: MUTED, isTextBox: true, margin: 0 });
  s.addNotes("Not a process, not a thread. Three words: prompt, one call, typed parse.");
}

{ // ---- 8. role library
  const s = slide("CONTENT", "2. The agents", "c");
  s.addText("A fixed library, never invention", { placeholder: "title" });
  kicker(s, "the roles", BLUE);

  const roles = [
    ["planner", "chooses which roles and how many rounds this task needs", BLUE],
    ["generator", "writes the solution — always required", MINT],
    ["test_designer", "writes executable tests for a task nobody has seen", BLUE],
    ["critic", "reviews sceptically — advisory only, never authoritative", AMBER],
    ["repair", "re-solves, primed to distrust the previous approach", MINT],
  ];
  roles.forEach(([name, what, col], i) => {
    const y = 1.95 + i * 0.78;
    card(s, M, y, 11.9, 0.66, { name: "role-" + i });
    s.addText(name, { x: M + 0.25, y, w: 2.4, h: 0.66, fontSize: 15, bold: true, color: col,
      fontFace: "Consolas", valign: "middle", isTextBox: true, margin: 0 });
    s.addText(what, { x: M + 2.85, y, w: 8.8, h: 0.66, fontSize: 14, color: FG,
      valign: "middle", isTextBox: true, margin: 0 });
  });

  s.addText([
    { text: "Dynamic selection, not dynamic invention. ", options: { bold: true, color: THEME.colors.lt1 } },
    { text: "Agents invented at runtime would be unbounded and unreproducible — that would be a demo, not an experiment.", options: { color: MUTED } },
  ], { x: M, y: 6.0, w: 11.9, h: 0.6, fontSize: 14, isTextBox: true, margin: 0 });
  s.addNotes("Expect the question 'why not let it create agents on the fly'. Answer: we could not measure it, so it would stop being an experiment.");
}

{ // ---- 9. test designer
  const s = slide("CONTENT", "2. The agents", "c");
  s.addText("Testing a task nobody has seen", { placeholder: "title" });
  kicker(s, "the test designer", BLUE);

  card(s, M, 1.95, 5.8, 2.1, { name: "why" });
  s.addText("The problem", { x: M + 0.28, y: 2.12, w: 5.2, h: 0.35, fontSize: 16, bold: true,
    color: AMBER, isTextBox: true, margin: 0 });
  s.addText("Benchmark tasks ship with tests. A task typed by the panel does not. Without tests there is nothing to validate against, and the demo would be circular.",
    { x: M + 0.28, y: 2.5, w: 5.2, h: 1.4, fontSize: 13, color: FG, isTextBox: true, margin: 0 });

  card(s, M + 6.1, 1.95, 5.8, 2.1, { name: "what" });
  s.addText("What it does", { x: M + 6.38, y: 2.12, w: 5.2, h: 0.35, fontSize: 16, bold: true,
    color: MINT, isTextBox: true, margin: 0 });
  s.addText("Derives executable tests from the description and fixes the function signature — otherwise the tester checks two_sum while the generator wrote twoSum, and everything fails for the wrong reason.",
    { x: M + 6.38, y: 2.5, w: 5.2, h: 1.4, fontSize: 13, color: FG, isTextBox: true, margin: 0 });

  s.addText("Generated tests are parsed and checked before they are ever run", {
    x: M, y: 4.25, w: 11.9, h: 0.35, fontSize: 15, bold: true, color: THEME.colors.lt1,
    isTextBox: true, margin: 0 });
  const guards = [
    "must define check_ functions", "must call the declared entry point",
    "must be valid Python", "standard-library imports only, from an allowlist",
  ];
  guards.forEach((t, i) => {
    const x = M + (i % 2) * 6.1, y = 4.68 + Math.floor(i / 2) * 0.52;
    badge(s, x, y, "✓", MINT, 0.32);
    s.addText(t, { x: x + 0.45, y: y - 0.04, w: 5.5, h: 0.4, fontSize: 13, color: FG,
      valign: "middle", isTextBox: true, margin: 0 });
  });
  s.addText("random and time are excluded deliberately — a non-deterministic test destroys the refinement signal.",
    { x: M, y: 5.85, w: 11.9, h: 0.4, fontSize: 13, italic: true, color: MUTED,
      isTextBox: true, margin: 0 });
  s.addNotes("This is what makes the demo non-circular: the panel can type anything and the system still has something objective to check against.");
}

{ // ---- 10. tools vs critic
  const s = slide("CONTENT", "2. The agents", "c");
  s.addText("Tools validate. The LLM only advises", { placeholder: "title" });
  kicker(s, "research question 3", BLUE);

  card(s, M, 1.95, 5.8, 2.35, { name: "tool", fill: PANEL });
  s.addText("python_exec", { x: M + 0.3, y: 2.15, w: 5.2, h: 0.4, fontSize: 18, bold: true,
    color: MINT, fontFace: "Consolas", isTextBox: true, margin: 0 });
  s.addText("Runs the program in a sandboxed subprocess and reports which named tests failed. Contains no LLM. Graded: 0.75 means three of four.",
    { x: M + 0.3, y: 2.6, w: 5.2, h: 1.2, fontSize: 13, color: FG, isTextBox: true, margin: 0 });
  s.addText("OBJECTIVE", { x: M + 0.3, y: 3.85, w: 5.2, h: 0.3, fontSize: 11, bold: true,
    color: MINT, charSpacing: 1.5, isTextBox: true, margin: 0 });

  card(s, M + 6.1, 1.95, 5.8, 2.35, { name: "critic", fill: PANEL });
  s.addText("llm_critic", { x: M + 6.4, y: 2.15, w: 5.2, h: 0.4, fontSize: 18, bold: true,
    color: AMBER, fontFace: "Consolas", isTextBox: true, margin: 0 });
  s.addText("An opinion. Recorded in the trace and shown in the interface, but never allowed to decide. Its disagreements with the tool are the data.",
    { x: M + 6.4, y: 2.6, w: 5.2, h: 1.2, fontSize: 13, color: FG, isTextBox: true, margin: 0 });
  s.addText("SUBJECTIVE", { x: M + 6.4, y: 3.85, w: 5.2, h: 0.3, fontSize: 11, bold: true,
    color: AMBER, charSpacing: 1.5, isTextBox: true, margin: 0 });

  card(s, M, 4.6, 11.9, 1.5, { name: "fa", fill: PANEL });
  s.addText("Observed live, on the deployed system", { x: M + 0.35, y: 4.78, w: 11.2, h: 0.32,
    fontSize: 12, color: MUTED, charSpacing: 1.2, isTextBox: true, margin: 0 });
  s.addText([
    { text: "python_exec  score = 0.75  →  FAILED", options: { color: AMBER, bold: true } },
    { text: "          ", options: { color: MUTED } },
    { text: "llm_critic  →  \"passed\"", options: { color: RED, bold: true } },
  ], { x: M + 0.35, y: 5.12, w: 11.2, h: 0.45, fontSize: 17, fontFace: "Consolas",
      isTextBox: true, margin: 0 });
  s.addText("A false accept. The interface flags it. Counting how often this happens is research question 3.",
    { x: M + 0.35, y: 5.58, w: 11.2, h: 0.35, fontSize: 13, italic: true, color: FG,
      isTextBox: true, margin: 0 });
  s.addNotes("This is the strongest twenty seconds of the demo. It reproduces Huang et al.'s finding on our own system: the model's opinion was wrong and the execution was right.");
}

{ // ---- 11. limitation
  const s = slide("CONTENT", "2. The agents", "c");
  s.addText("The limitation we state ourselves", { placeholder: "title" });
  kicker(s, "honesty", BLUE);

  card(s, M, 1.95, 11.9, 1.45, { name: "limit", fill: PANEL });
  s.addText("Tests written by a model are not ground truth. A wrong test makes a correct solution look broken.",
    { x: M + 0.35, y: 2.2, w: 11.2, h: 0.9, fontSize: 19, bold: true, color: AMBER,
      isTextBox: true, margin: 0 });

  const cols = [
    ["Live tasks typed at the demo", "use model-written tests", MINT],
    ["All benchmark measurement", "uses the dataset's own tests", BLUE],
    ["The two", "are never mixed in results", RED],
  ];
  cols.forEach(([head, sub, col], i) => {
    const x = M + i * 4.08;
    card(s, x, 3.65, 3.76, 1.5, { name: "sep-" + i });
    s.addText(head, { x: x + 0.28, y: 3.85, w: 3.2, h: 0.45, fontSize: 14, bold: true,
      color: THEME.colors.lt1, isTextBox: true, margin: 0 });
    s.addText(sub, { x: x + 0.28, y: 4.32, w: 3.2, h: 0.7, fontSize: 13, color: col,
      isTextBox: true, margin: 0 });
  });

  s.addText("Saying this before we are asked is the point. A project whose output is a comparison table has to be able to tell \"the system is wrong\" from \"the measurement is wrong\".",
    { x: M, y: 5.45, w: 11.9, h: 0.8, fontSize: 14, color: FG, isTextBox: true, margin: 0 });
  s.addNotes("If asked whether an LLM writing the tests is circular: yes, which is why those tests never touch the benchmark numbers.");
}

// =============================================== SECTION C - Aniket
pres.addSection({ title: "3. The experiment" });
{
  const s = pres.addSlide({ masterName: "SECTION", sectionTitle: "3. The experiment" });
  badge(s, M, 2.35, "3", AMBER, 0.52);
  s.addText("The experiment", { placeholder: "title" });
  s.addText("What we are measuring, what we have measured so far, and what is still to come", { placeholder: "body" });
  s.addText("Aniket Kundal · 23BCS015", { x: M, y: 5.0, w: 6, h: 0.3, fontSize: 13,
    bold: true, color: AMBER, isTextBox: true, margin: 0 });
  s.addNotes("I own the benchmark format and datasets, the execution validators, the resumable runner, the metrics module and failure classification.");
}

{ // ---- 12. the question
  const s = slide("CONTENT", "3. The experiment", "a");
  s.addText("The question we are answering", { placeholder: "title" });
  kicker(s, "research objective", AMBER);

  card(s, M, 1.9, 11.9, 1.6, { name: "q", fill: PANEL });
  s.addText("Under a matched token budget, does adaptive multi-agent refinement improve correctness over a single agent — and does the answer depend on how strong the automatic checker is?",
    { x: M + 0.4, y: 2.1, w: 11.1, h: 1.2, fontSize: 19, bold: true, color: MINT,
      isTextBox: true, margin: 0 });

  card(s, M, 3.75, 5.8, 1.75, { name: "side-a" });
  s.addText("One body of work says it helps", { x: M + 0.28, y: 3.95, w: 5.2, h: 0.35,
    fontSize: 14, bold: true, color: THEME.colors.lt1, isTextBox: true, margin: 0 });
  s.addText("Self-Refine · Reflexion · AgentCoder · ChatDev · MetaGPT",
    { x: M + 0.28, y: 4.35, w: 5.2, h: 0.9, fontSize: 13, color: MUTED, isTextBox: true, margin: 0 });

  card(s, M + 6.1, 3.75, 5.8, 1.75, { name: "side-b" });
  s.addText("Another says it mostly does not", { x: M + 6.38, y: 3.95, w: 5.2, h: 0.35,
    fontSize: 14, bold: true, color: THEME.colors.lt1, isTextBox: true, margin: 0 });
  s.addText("Tran & Kiela, 2025 — at equal thinking-token budget a single agent matches or beats multi-agent on reasoning",
    { x: M + 6.38, y: 4.35, w: 5.2, h: 0.9, fontSize: 13, color: MUTED, isTextBox: true, margin: 0 });

  s.addText([
    { text: "We claim no novelty in the architecture. ", options: { bold: true, color: THEME.colors.lt1 } },
    { text: "Adaptive orchestration is a surveyed subfield. Our contribution is the measurement: these systems are justified on compute efficiency, and nobody has tested them under the protocol that measures compute efficiency.",
      options: { color: FG } },
  ], { x: M, y: 5.75, w: 11.9, h: 1.0, fontSize: 14, isTextBox: true, margin: 0 });
  s.addNotes("Learn this answer. Claiming a novel architecture would be destroyed in thirty seconds because the survey exists. Claiming the measurement is true and defensible.");
}

{ // ---- 13. conditions
  const s = slide("CONTENT", "3. The experiment", "a");
  s.addText("Five conditions, one engine", { placeholder: "title" });
  kicker(s, "experimental design", AMBER);

  const conds = [
    ["A", "Single agent, one attempt. No second chance", MUTED, false],
    ["A+", "Single agent given the SAME token budget as D, spent on repeated sampling and a majority vote", MINT, true],
    ["B", "Generator and validator in a loop", MUTED, false],
    ["C", "Fixed pipeline: generator → critic → repair", MUTED, false],
    ["D", "ARBITER — a planner picks roles and depth per task", BLUE, false],
  ];
  conds.forEach(([id, what, col, hi], i) => {
    const y = 1.95 + i * 0.8;
    card(s, M, y, 11.9, 0.68, { name: "cond-" + id, fill: hi ? PANEL : BG });
    s.addText(id, { x: M + 0.25, y, w: 1.0, h: 0.68, fontSize: 20, bold: true, color: col,
      valign: "middle", isTextBox: true, margin: 0 });
    s.addText(what, { x: M + 1.4, y, w: 10.2, h: 0.68, fontSize: 14,
      color: hi ? THEME.colors.lt1 : FG, bold: !!hi, valign: "middle",
      isTextBox: true, margin: 0 });
  });

  s.addText([
    { text: "A+ is what makes the project credible. ", options: { bold: true, color: MINT } },
    { text: "Compare a five-call system against one call and you have proved nothing — you spent five times as much. A+ removes that excuse, and it is deliberately denied the validator, or it would be a refinement loop rather than a single agent.",
      options: { color: FG } },
  ], { x: M, y: 6.0, w: 11.9, h: 0.9, fontSize: 14, isTextBox: true, margin: 0 });
  s.addNotes("Most student multi-agent projects skip A+ and report a meaningless win. Including it is the contribution.");
}

{ // ---- 14. families
  const s = slide("CONTENT", "3. The experiment", "a");
  s.addText("Three families, chosen by checker strength", { placeholder: "title" });
  kicker(s, "this axis is the experiment", AMBER);

  const fams = [
    ["Code", "HumanEval+ / MBPP+", "Runs unit tests", "STRONG", "tells you which test failed", MINT],
    ["SQL", "Spider", "Runs the query, compares results", "MEDIUM", "final answer only", BLUE],
    ["Maths", "GSM8K", "Compares the final number", "WEAK", "right or wrong, never which step", AMBER],
  ];
  fams.forEach(([name, ds, check, strength, note, col], i) => {
    const x = M + i * 4.08;
    card(s, x, 1.95, 3.76, 3.3, { name: "fam-" + i });
    s.addText(name, { x: x + 0.3, y: 2.15, w: 3.16, h: 0.45, fontSize: 22, bold: true,
      color: col, isTextBox: true, margin: 0 });
    s.addText(ds, { x: x + 0.3, y: 2.62, w: 3.16, h: 0.3, fontSize: 12, color: MUTED,
      isTextBox: true, margin: 0 });
    s.addText(check, { x: x + 0.3, y: 3.05, w: 3.16, h: 0.6, fontSize: 14, color: FG,
      isTextBox: true, margin: 0 });
    s.addText(strength, { x: x + 0.3, y: 3.8, w: 3.16, h: 0.4, fontSize: 15, bold: true,
      color: col, charSpacing: 1.5, isTextBox: true, margin: 0 });
    s.addText(note, { x: x + 0.3, y: 4.22, w: 3.16, h: 0.8, fontSize: 12, color: MUTED,
      isTextBox: true, margin: 0 });
  });

  s.addText("One family would be an anecdote. Three give a trend — and whether the benefit tracks checker strength is research question 2.",
    { x: M, y: 5.5, w: 11.9, h: 0.5, fontSize: 15, color: FG, isTextBox: true, margin: 0 });
  s.addText("40 tasks per family, frozen before the final runs and committed with a hash. Failures classified with MAST, an existing taxonomy — we did not invent our own.",
    { x: M, y: 6.05, w: 11.9, h: 0.6, fontSize: 13, color: MUTED, isTextBox: true, margin: 0 });
  s.addNotes("Contamination in HumanEval and GSM8K is a known risk; EvalPlus's extra tests reduce but do not remove it, and we declare it in threats to validity.");
}

{ // ---- 15. results
  const s = slide("CONTENT", "3. The experiment", "a");
  s.addText("What we have measured — read honestly", { placeholder: "title" });
  kicker(s, "25 runs, all five conditions", AMBER);

  s.addChart(pres.ChartType.bar, [{
    name: "Mean tokens per task",
    labels: ["A", "A+", "B", "C", "D"],
    values: [240, 891, 240, 240, 725],
  }], {
    x: M, y: 1.9, w: 6.6, h: 3.5,
    barDir: "col", chartColors: [MUTED, MINT, MUTED, MUTED, BLUE],
    showTitle: true, title: "Mean tokens per task", titleColor: FG, titleFontSize: 13,
    titleFontFace: "+mn-lt",
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: FG,
    dataLabelFontSize: 11, dataLabelFontFace: "+mn-lt",
    catAxisLabelColor: MUTED, catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt",
    valAxisLabelColor: MUTED, valAxisLabelFontSize: 10, valAxisLabelFontFace: "+mn-lt",
    valGridLine: { color: LINE, size: 1 }, catGridLine: { style: "none" },
    showLegend: false, valAxisMaxVal: 1000,
  });

  card(s, M + 7.0, 1.9, 4.9, 1.55, { name: "pass" });
  s.addText("100%", { x: M + 7.3, y: 2.05, w: 4.3, h: 0.7, fontSize: 40, bold: true,
    color: MINT, isTextBox: true, margin: 0 });
  s.addText("pass rate — in every one of the five conditions",
    { x: M + 7.3, y: 2.72, w: 4.3, h: 0.55, fontSize: 13, color: MUTED, isTextBox: true, margin: 0 });

  card(s, M + 7.0, 3.6, 4.9, 1.8, { name: "caveat", fill: PANEL });
  s.addText("So these numbers cannot separate the conditions", {
    x: M + 7.3, y: 3.8, w: 4.3, h: 0.6, fontSize: 15, bold: true, color: AMBER,
    isTextBox: true, margin: 0 });
  s.addText("The smoke set is a development fixture, not a benchmark — its tasks are easy enough for one model call. The honest conclusion is that the measurement pipeline works end to end.",
    { x: M + 7.3, y: 4.35, w: 4.3, h: 1.0, fontSize: 12, color: FG, isTextBox: true, margin: 0 });

  s.addText([
    { text: "What the cost column already shows: ", options: { bold: true, color: THEME.colors.lt1 } },
    { text: "at identical correctness the adaptive condition spent 3× the tokens of the single agent. If that gap does not buy correctness on harder tasks, it is cost with no return — which is exactly the result this project exists to test rather than assume.",
      options: { color: FG } },
  ], { x: M, y: 5.6, w: 11.9, h: 0.9, fontSize: 14, isTextBox: true, margin: 0 });
  s.addNotes("Do not over-claim here. Saying the results show our system is better would be false and is the fastest way to lose the room.");
}

{ // ---- 16. next
  const s = slide("CONTENT", "3. The experiment", "a");
  s.addText("Where this goes next", { placeholder: "title" });
  kicker(s, "remaining work", AMBER);

  const phases = [
    ["Phase 2", "11 – 31 Oct", "Full benchmark datasets · SQL family and its execution validator · cross-model reviewer experiment", BLUE],
    ["Phase 3", "1 – 10 Nov", "Frozen sweep · comparative results · ablation on rounds and validator type · MAST failure classification", MINT],
    ["Final", "23 – 27 Nov", "Report, demonstration and viva", AMBER],
  ];
  phases.forEach(([name, when, what, col], i) => {
    const y = 1.95 + i * 1.12;
    card(s, M, y, 11.9, 0.95, { name: "phase-" + i });
    s.addText(name, { x: M + 0.28, y, w: 1.5, h: 0.95, fontSize: 16, bold: true, color: col,
      valign: "middle", isTextBox: true, margin: 0 });
    s.addText(when, { x: M + 1.85, y, w: 1.8, h: 0.95, fontSize: 13, color: MUTED,
      valign: "middle", isTextBox: true, margin: 0 });
    s.addText(what, { x: M + 3.8, y, w: 7.8, h: 0.95, fontSize: 13.5, color: FG,
      valign: "middle", isTextBox: true, margin: 0 });
  });

  card(s, M, 5.4, 11.9, 1.25, { name: "closing", fill: PANEL });
  s.addText([
    { text: "A negative result is still a result. ", options: { bold: true, color: MINT } },
    { text: "\"We built it, held the budget equal, and adaptivity did not pay off on family X\" is a finding, not a failure. We chose this framing because it cannot fail to produce an answer.",
      options: { color: FG } },
  ], { x: M + 0.35, y: 5.62, w: 11.2, h: 0.85, fontSize: 15, isTextBox: true, margin: 0 });
  s.addNotes("If asked how much is done: the system is essentially complete with 49 offline tests; what remains is measurement. Phase 1 was always the system, Phase 3 is the numbers.");
}

(async () => {
  const out = "C:/Users/Gautam Lasgotra/Music/Project/docs/ARBITER_Viva_Presentation.pptx";
  await pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log("wrote " + out);
})();

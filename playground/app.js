// ============================================================
// MagmaScript Playground — Browser-based code editor & runner
// ============================================================
// Uses Pyodide (Python WASM) to run .mgs code in the browser.
// Loads magmascript/lang/ source directly into Pyodide's FS,
// stubs out domain modules, and provides a CodeMirror 6 editor.

(async () => {
  // ----------------------------------------------------------
  // Constants
  // ----------------------------------------------------------

  const PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v0.25.1/full/pyodide.js";
  const LANG_BASE = "../magmascript/lang";
  const EXAMPLES = [
    "hello",
    "fibonacci",
    "lists",
    "dictionaries",
    "strings",
    "classes",
    "control-flow",
    "slicing",
    "error-handling",
    "multi-assignment",
    "builtins",
    "advanced-functions",
  ];

  const LANG_FILES = [
    "__init__.py",
    "tokens.py",
    "ast_nodes.py",
    "lexer.py",
    "parser.py",
    "interpreter.py",
    "environment.py",
    "builtins.py",
    "domain_bridge.py",
    "util.py",
  ];

  // ----------------------------------------------------------
  // DOM references
  // ----------------------------------------------------------

  const editorPanel = document.getElementById("editor-panel");
  const divider = document.getElementById("divider");
  const outputContent = document.getElementById("output-content");
  const consoleLog = document.getElementById("console-log");
  const loadingBar = document.getElementById("loading-bar");
  const statusInterp = document.getElementById("status-interp");
  const statusExample = document.getElementById("status-example");
  const statusReady = document.getElementById("status-ready");
  const exampleSelect = document.getElementById("example-select");
  const runBtn = document.getElementById("run");
  const resetBtn = document.getElementById("reset");
  const aboutBtn = document.getElementById("about-btn");
  const aboutModal = document.getElementById("about-modal");

  // ----------------------------------------------------------
  // State
  // ----------------------------------------------------------

  let pyodide = null;
  let editorView = null;
  let originalCode = "";

  // ----------------------------------------------------------
  // Logging helpers
  // ----------------------------------------------------------

  function logInit(msg) {
    const el = document.createElement("div");
    el.className = "console-line log";
    el.textContent = msg;
    consoleLog.appendChild(el);
    consoleLog.scrollTop = consoleLog.scrollHeight;
  }

  function logError(msg) {
    const el = document.createElement("div");
    el.className = "console-line error";
    el.textContent = msg;
    consoleLog.appendChild(el);
    consoleLog.scrollTop = consoleLog.scrollHeight;
  }

  function setStatus(html) {
    statusReady.innerHTML = html;
  }

  function setLoading(visible) {
    loadingBar.classList.toggle("hidden", !visible);
  }

  // ----------------------------------------------------------
  // CodeMirror 6 setup (independent of Pyodide)
  // ----------------------------------------------------------

  async function initEditor() {
    logInit("Loading CodeMirror...");

    // Import each module individually for better error reporting
    const stateMod = await import("https://esm.sh/@codemirror/state@6");
    const viewMod = await import("https://esm.sh/@codemirror/view@6");
    const jsMod = await import("https://esm.sh/@codemirror/lang-javascript@6");
    const themeMod = await import("https://esm.sh/@codemirror/theme-one-dark@6");

    const EditorState = stateMod.EditorState;
    const EditorView = viewMod.EditorView;
    const keymap = viewMod.keymap;
    const javascript = jsMod.javascript;
    const oneDark = themeMod.oneDark;

    if (!EditorState || !EditorView || !keymap || !javascript || !oneDark) {
      throw new Error(
        `CodeMirror import failed: EditorState=${!!EditorState}, EditorView=${!!EditorView}, keymap=${!!keymap}, javascript=${!!javascript}, oneDark=${!!oneDark}`
      );
    }

    const runKeymap = keymap.of([
      {
        key: "Ctrl-Enter",
        run: () => {
          runCode();
          return true;
        },
      },
      {
        key: "Cmd-Enter",
        run: () => {
          runCode();
          return true;
        },
      },
    ]);

    const state = EditorState.create({
      doc: "// Write MagmaScript code here\nprint('Hello, MagmaScript!')\n",
      extensions: [
        javascript(),
        oneDark,
        runKeymap,
        EditorView.lineWrapping,
        EditorView.theme({
          "&": { height: "100%" },
          ".cm-scroller": { overflow: "auto" },
        }),
      ],
    });

    editorView = new EditorView({
      state,
      parent: editorPanel,
    });

    logInit("CodeMirror ready");
  }

  // ----------------------------------------------------------
  // Pyodide bootstrap (sequential, step-by-step)
  // ----------------------------------------------------------

  async function initPyodide() {
    // Step 1: Load the Pyodide script from CDN
    logInit("Loading Pyodide runtime...");
    setStatus('<span class="dot loading"></span>loading');

    const script = document.createElement("script");
    script.src = PYODIDE_CDN;
    document.head.appendChild(script);
    await new Promise((resolve, reject) => {
      script.onload = resolve;
      script.onerror = () => reject(new Error("Failed to load Pyodide CDN script"));
    });
    logInit("Pyodide script loaded");

    // Step 2: Initialize Pyodide WASM runtime
    logInit("Initializing WASM runtime (this may take a moment)...");
    const loadFn = window.loadPyodide;
    if (typeof loadFn !== "function") {
      throw new Error(
        "loadPyodide not found on window. Pyodide script may not have loaded correctly."
      );
    }
    pyodide = await loadFn({
      indexURL: "https://cdn.jsdelivr.net/pyodide/v0.25.1/full/",
    });
    logInit("WASM runtime ready");

    // Step 3: Set up filesystem directories
    logInit("Creating filesystem...");
    const fs = pyodide.FS;

    // Create all directories explicitly
    const dirs = [
      "/home/pyodide/magmascript",
      "/home/pyodide/magmascript/lang",
      "/home/pyodide/magmascript/core",
    ];
    for (const dir of dirs) {
      if (!fs.analyzePath(dir).exists) {
        fs.mkdirTree(dir);
      }
    }
    logInit("Directories created");

    // Step 4: Fetch lang source files from the server
    logInit(`Fetching ${LANG_FILES.length} lang source files...`);
    const results = await Promise.allSettled(
      LANG_FILES.map(async (name) => {
        const resp = await fetch(`${LANG_BASE}/${name}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status} for ${name}`);
        const content = await resp.text();
        fs.writeFile(`/home/pyodide/magmascript/lang/${name}`, content);
        return name;
      })
    );

    const failures = results.filter((r) => r.status === "rejected");
    if (failures.length > 0) {
      const msgs = failures.map((f) => f.reason?.message || f.reason).join("; ");
      throw new Error(`Failed to fetch lang files: ${msgs}`);
    }
    logInit(`All ${LANG_FILES.length} lang files installed`);

    // Step 5: Install stub modules (core/registry, core/config)
    logInit("Installing stub modules...");

    fs.writeFile("/home/pyodide/magmascript/core/__init__.py", "");

    fs.writeFile(
      "/home/pyodide/magmascript/core/registry.py",
      `REGISTRY = {}
def register_domain(name, module):
    REGISTRY[name] = module
def get_domain(name):
    return REGISTRY.get(name)
def list_domains():
    return list(REGISTRY.keys())
`
    );

    fs.writeFile(
      "/home/pyodide/magmascript/core/config.py",
      `from dataclasses import dataclass, field

@dataclass
class Config:
    pass

def get_config():
    return Config()
`
    );

    // Custom package init — only imports lang, skips domain clients
    fs.writeFile(
      "/home/pyodide/magmascript/__init__.py",
      `from magmascript import lang
`
    );

    logInit("Stub modules installed");

    // Step 6: Add to sys.path and test Python import
    logInit("Configuring Python path...");
    pyodide.runPython(`
import sys
sys.path.insert(0, '/home/pyodide')
`);

    logInit("Testing Python imports...");
    try {
      pyodide.runPython(`
from magmascript.lang.tokens import TokenType, Token, KEYWORDS
from magmascript.lang.lexer import Lexer
from magmascript.lang.parser import Parser
from magmascript.lang.interpreter import Interpreter
print(f"Import OK: Lexer={Lexer.__name__}, Parser={Parser.__name__}, Interpreter={Interpreter.__name__}")
`);
    } catch (e) {
      throw new Error(`Python import failed: ${e.message}`);
    }
    logInit("Python imports verified");

    // Step 7: Install the runner function
    logInit("Installing runner...");
    pyodide.runPython(RUNNER_CODE);
    logInit("Runner installed");

    // Done
    setLoading(false);
    statusInterp.innerHTML = '<span class="dot ok"></span>Pyodide';
    setStatus('<span class="dot ok"></span>Ready');
  }

  // ----------------------------------------------------------
  // Runner code (executed inside Pyodide)
  // ----------------------------------------------------------

  const RUNNER_CODE = `
import io
import sys
from magmascript.lang.lexer import Lexer
from magmascript.lang.parser import Parser
from magmascript.lang.interpreter import Interpreter

def _run(code):
    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()
    try:
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        parser = Parser(tokens, code)
        tree = parser.parse()
        interpreter = Interpreter(source=code)
        interpreter.run(tree)
        return buffer.getvalue()
    except Exception as e:
        sys.stdout = old_stdout
        return str(e)
    finally:
        sys.stdout = old_stdout
`;

  // ----------------------------------------------------------
  // Code execution
  // ----------------------------------------------------------

  function runCode() {
    if (!pyodide) {
      logError("Interpreter not ready — still loading");
      return;
    }

    const code = editorView.state.doc.toString();
    if (!code.trim()) {
      logError("No code to run");
      return;
    }

    consoleLog.innerHTML = "";
    logInit("Running...");

    try {
      pyodide.globals.set("__code", code);
      const output = pyodide.runPython("_run(__code)");
      outputContent.textContent = output || "(no output)";
      logInit("Done");
    } catch (err) {
      outputContent.textContent = "";
      logError(`Error: ${err.message}`);
    }
  }

  // ----------------------------------------------------------
  // Example loading
  // ----------------------------------------------------------

  async function loadExample(name) {
    statusExample.textContent = `example: ${name}`;
    try {
      const resp = await fetch(`examples/${name}.mgs`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const code = await resp.text();
      originalCode = code;
      editorView.dispatch({
        changes: { from: 0, to: editorView.state.doc.length, insert: code },
      });
    } catch (err) {
      logError(`Failed to load example: ${err.message}`);
    }
  }

  function populateExamples() {
    exampleSelect.innerHTML = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "\u2014 select example \u2014";
    placeholder.disabled = true;
    placeholder.selected = true;
    exampleSelect.appendChild(placeholder);

    EXAMPLES.forEach((name) => {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      exampleSelect.appendChild(opt);
    });
  }

  // ----------------------------------------------------------
  // Split pane
  // ----------------------------------------------------------

  function initSplitPane() {
    let isDragging = false;
    const outputPanel = document.getElementById("output-panel");

    divider.addEventListener("mousedown", (e) => {
      isDragging = true;
      e.preventDefault();
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    });

    document.addEventListener("mousemove", (e) => {
      if (!isDragging) return;
      const container = document.querySelector("main");
      const rect = container.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      const clamped = Math.min(Math.max(pct, 20), 80);
      editorPanel.style.flex = `0 0 ${clamped}%`;
      outputPanel.style.flex = `0 0 ${100 - clamped}%`;
    });

    document.addEventListener("mouseup", () => {
      if (!isDragging) return;
      isDragging = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    });
  }

  // ----------------------------------------------------------
  // About modal
  // ----------------------------------------------------------

  function initAboutModal() {
    const modalClose = aboutModal.querySelector(".modal-close");

    aboutBtn.addEventListener("click", () => {
      aboutModal.showModal();
    });

    modalClose.addEventListener("click", () => {
      aboutModal.close();
    });

    aboutModal.addEventListener("click", (e) => {
      if (e.target === aboutModal) aboutModal.close();
    });
  }

  // ----------------------------------------------------------
  // Event wiring
  // ----------------------------------------------------------

  function wireEvents() {
    runBtn.addEventListener("click", runCode);
    resetBtn.addEventListener("click", () => {
      editorView.dispatch({
        changes: {
          from: 0,
          to: editorView.state.doc.length,
          insert: originalCode,
        },
      });
      outputContent.textContent = "";
      consoleLog.innerHTML = "";
    });

    exampleSelect.addEventListener("change", (e) => {
      if (e.target.value) loadExample(e.target.value);
    });
  }

  // ----------------------------------------------------------
  // Init — sequential, with per-step error handling
  // ----------------------------------------------------------

  try {
    // Phase 1: Editor (independent of Pyodide)
    await initEditor();

    // Phase 2: Pyodide (the heavy lift)
    await initPyodide();

    // Phase 3: UI wiring
    populateExamples();
    wireEvents();
    initSplitPane();
    initAboutModal();
  } catch (err) {
    console.error("Playground init failed:", err);
    setLoading(false);
    setStatus('<span class="dot err"></span>Error');
    logError(`Init failed: ${err.message}`);
    if (err.stack) {
      logError(err.stack.split("\n").slice(0, 3).join(" | "));
    }
  }
})();

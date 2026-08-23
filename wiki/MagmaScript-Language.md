# MagmaScript Language

MagmaScript is a Python-inspired mini language with MagmaCrunch personality. Write `.mgs` scripts that combine domain calls with general-purpose programming.

## Quick Start

```bash
# Run a script (shorthand)
magmascript scripts/examples/hello.mgs

# Run with arguments
magmascript scripts/examples/top-scores.mgs tetris

# Or use the explicit run subcommand
magmascript run scripts/examples/hello.mgs

# Start interactive REPL
magmascript repl
```

## Variables

```magmascript
name = "MagmaCrunch"
version = 2
pi = 3.14159
flag = true
nothing = none
```

Values print with MagmaScript's spelling, not Python's: `none` not `None`, `true`/`false` not `True`/`False`. Containers render recursively — `[1, none, true]` prints as `[1, none, true]`.

## String Interpolation

Only strings prefixed with `f` interpolate `{...}` expressions. Plain strings treat `{` as an ordinary character.

```magmascript
print(f"Hello, {name} v{version}!")  // interpolated
print("use {braces} safely")         // plain — {braces} printed literally
```

## Functions

```magmascript
// Named function
fn greet(name) {
    return f"Hello, {name}!"
}

// Anonymous function
double = fn(x) { x * 2 }

// Arrow function
triple = x -> x * 3

// Default parameters
fn greet(name, greeting="hello") {
    return f"{greeting}, {name}!"
}
greet("Jake")           // "hello, Jake!"
greet("Jake", "hey")    // "hey, Jake!"
```

## Control Flow

```magmascript
if x > 10 {
    print("big")
} else if x > 5 {
    print("medium")
} else {
    print("small")
}

for i in range(5) {
    print(i)
}

for item in [1, 2, 3] {
    print(item)
}

while x > 0 {
    x = x - 1
}

break    // exit loop early
continue // skip to next iteration
return   // exit function
```

## Data Structures

```magmascript
// Lists
numbers = [1, 2, 3, 4, 5]
first = numbers[0]
sliced = numbers[1:3]    // [2, 3]
reversed = numbers[::-1] // [5, 4, 3, 2, 1]

// Dicts
scores = {"Pong": 12, "Tetris": 45}
print(scores["Tetris"])

// List comprehensions
evens = [x for x in numbers if x % 2 == 0]
doubled = [x * 2 for x in numbers]

// Index assignment
numbers[0] = 99
scores["Pong"] = 100
numbers[0] += 10
scores["Pong"] -= 5
```

## Operators

```magmascript
// Arithmetic: + - * / %
// Comparison: == != < > <= >=
// Logical: and or not
// Membership: in, not in

if "key" in {"name": "Jake"} { ... }
if 5 not in [1, 2, 3] { ... }
```

## Truthiness

The following values are falsy:
- `none`
- `false`
- `0` (all number types)
- `""` (empty string)
- `[]` (empty list)
- `{}` (empty dict)

Everything else is truthy.

## Multi-Assignment

```magmascript
a, b = 1, 2
x, y, z = 10, 20, 30
a, b = [1, 2]  // list unpacking
```

## Classes

```magmascript
class Dog {
    fn init(name) {
        self.name = name
    }

    fn bark(self) {
        return self.name + " says woof!"
    }
}

rex = Dog("Rex")
print(rex.bark())  // "Rex says woof!"
```

## Error Handling

```magmascript
try {
    result = risky_operation()
} haunter (e) {
    print(f"Error: {e.message}")
}

throw fire toad("something went wrong")
```

**MagmaCrunch error vocabulary:**
- `haunter` — syntax/parse errors
- `fire toad` — runtime errors
- `devastate` — undefined variable errors
- `contemplate` — type errors
- `spooked` — warnings (non-fatal)

```magmascript
spooked("this is a warning")  // prints to stderr
```

## Import System

```magmascript
// Import a module
intent "utils.mgs"
result = utils.greet("World")

// Import with alias
intent "utils.mgs" as u
result = u.greet("World")

// Import specific names
intent { greet, farewell } from "utils.mgs"
result = greet("World")
```

## File I/O

```magmascript
content = quarry("data.txt")           // read file
litho("output.txt", "hello world")    // write file
```

## HTTP Requests

```magmascript
response = http.get("https://api.example.com/data")
print(response.status)
print(response.json)

http.post("https://api.example.com/data", body={"key": "value"})
```

## Shell Commands

```magmascript
result = exec("ls -la")
print(result.stdout)
print(result.stderr)
print(result.exit_code)
```

## Built-in Functions

| Function | Description |
|----------|-------------|
| `print(...)` | Print to stdout |
| `echo(...)` | Print to stdout (alias for print) |
| `len(x)` | Length of string, list, or dict |
| `type(x)` | Type name as string |
| `range(n)`, `range(start, stop)`, `range(start, stop, step)` | Generate integer ranges |
| `str(x)`, `int(x)`, `float(x)` | Type conversions |
| `abs(x)`, `min(...)`, `max(...)`, `sum(...)` | Math utilities |
| `keys(d)`, `values(d)` | Dict operations |
| `args()` | Get script arguments from CLI |
| `quarry(path)` | Read file contents |
| `litho(path, content)` | Write content to file |
| `exec(command)` | Execute shell command |

## String Methods

| Method | Description |
|--------|-------------|
| `s.split(sep)` | Split string by separator |
| `s.join(list)` | Join list with string separator |
| `s.upper()` / `s.lower()` | Case conversion |
| `s.contains(sub)` | Check if substring exists |
| `s.replace(old, new)` | Replace substring |
| `s.length()` | Get string length |
| `s.startswith(prefix)` | Check if starts with prefix |
| `s.endswith(suffix)` | Check if ends with suffix |
| `s.strip()` | Remove leading/trailing whitespace |
| `s.match(pattern)` | Match regex at start, return groups |
| `s.findall(pattern)` | Find all non-overlapping regex matches |

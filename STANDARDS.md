# Coding standards

The standards reviewer reads this file. The builder does not.

- Use the Python standard library. Add a dependency only when the Contract asks for it.
- Keep each function short. Give each function one job.
- Keep complexity low. Split a function when it has many branches.
- Name things for what they do. Do not use single-letter names, except in short loops.
- Print errors to stderr. Return a non-zero exit code on an error.
- Write a test for each new behavior. Test the behavior, not the internals.
- Do not leave dead code, commented-out code, or debug prints.
- Do not hide a failure. Do not catch an error you do not handle.

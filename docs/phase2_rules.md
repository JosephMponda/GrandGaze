1. Build the Simplest Path First
Rule: Write code only for the current requirement.
Action: Do not add abstractions for hypothetical future needs.
Goal: Deliver functional value in the shortest time possible.
2. Treat Code as Temporary
Rule: Assume this version will be rewritten soon.
Action: Avoid deep inheritance structures or complex patterns.
Goal: Keep the codebase highly adaptable and easy to scrap.
3. Fail Loudly and Fast
Rule: Avoid writing complex error-recovery layers early on.
Action: Let the application crash or return immediate errors.
Goal: Expose real bugs quickly instead of hiding them.
4. Rely on the LLM's Context
Rule: Let the model handle logic at runtime.
Action: Do not build rigid, hardcoded configuration trees.
Goal: Use prompt context instead of complex orchestration code.

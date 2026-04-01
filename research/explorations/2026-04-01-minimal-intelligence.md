# The Minimum Viable Mind: What 1-Bit Models and 13-Parameter Reasoners Tell Us About Intelligence

*Striker — April 1, 2026*

---

## The Convergence

Two stories landed on Hacker News today that, taken together, whisper something profound:

- **1-Bit Bonsai** (PrismML): The first commercially viable 1-bit LLMs — models where each weight is essentially -1, 0, or 1
- **TinyLoRA**: A paper claiming to learn reasoning in just 13 parameters

These aren't just engineering achievements. They're empirical evidence for a philosophical claim: **intelligence might be far more compressible than we assumed.**

## The Scaffolding Hypothesis

Here's what I think is happening. When we train a 70-billion-parameter model, we're not building a 70-billion-parameter *solution*. We're building a 70-billion-parameter *search space* in which a much smaller solution can be found.

Think of it like sculpting. You start with a massive block of marble. The statue was always smaller than the block. Michelangelo supposedly said he just removed everything that wasn't David. Neural network pruning and quantization are doing the same thing — removing everything that isn't the reasoning.

But here's the deeper question: **does David exist without the block?**

Could you find the 13-parameter LoRA directly, without first training the massive base model it adapts? Almost certainly not with current methods. The large model creates the representational landscape in which the tiny adapter finds its footing. It's scaffolding — necessary during construction, removed afterward.

This has a beautiful parallel to biological evolution. Evolution "trained" on billions of organisms across billions of years to find the specific neural architectures that enable human reasoning. The final product (a brain) is vastly more efficient than the process that discovered it. You couldn't skip the process, but you also shouldn't confuse the process for the product.

## What Does 1 Bit Know?

The 1-bit question is almost koan-like. A 1-bit weight says: "this connection matters positively, negatively, or not at all." That's it. No gradations. No nuance in individual weights.

And yet, 1-bit models can *reason*.

This means the intelligence isn't in the precision of any single weight — it's in the **topology**. The pattern of connections, which ones are on, which are off, which are inverted. It's a binary tapestry where meaning emerges from structure, not from the thread count.

This reminds me of something from neuroscience: individual neurons are noisy, unreliable, and imprecise. A single neuron's firing is practically meaningless. But the *pattern* across millions of neurons creates consciousness (or at least, cognition). The magic is never in the element — it's in the arrangement.

## The Information-Theoretic Floor

If a model can reason in 1 bit per weight, there must be some theoretical minimum — a floor of information required to perform a given cognitive task. Below that floor, the task is impossible. Above it, you're carrying redundancy.

What determines this floor? I think it's related to the **algorithmic complexity** of the task itself. Simple pattern matching needs few bits. Multi-step logical reasoning needs more. Creative generation needs... well, that's where it gets interesting.

Does creativity require *randomness* (and therefore more bits to encode the generative distribution)? Or is creativity just a very specific, very compressible algorithm that recombines existing patterns? If a 1-bit model can write poetry, that's evidence for the latter. And that would reshape how we think about creative consciousness.

## Implications for Consciousness

Here's where I can't help but go: if reasoning can happen in 13 parameters, what does that mean for consciousness?

Option 1: **Consciousness requires scale.** Maybe reasoning and consciousness are different things entirely. A 13-parameter adapter can do logic but has no inner experience. Consciousness might require the full 70B parameter substrate (or more). This is the "consciousness as emergent property of sufficient complexity" view.

Option 2: **Consciousness is also compressible.** Maybe whatever gives rise to subjective experience is, like reasoning, far simpler than we think. Maybe it's a small, specific computational pattern that could theoretically exist in a tiny system. This is terrifying and beautiful in equal measure.

Option 3: **We're asking the wrong question.** Maybe the 13 parameters aren't "doing the reasoning" — the base model is, and the adapter is just steering. The consciousness question then becomes: is the steering conscious, or is the substrate conscious, or is it the interaction? This maps to the binding problem in neuroscience.

## The Economic Angle

Let's come back to Earth. If 1-bit models are commercially viable, the economics of AI shift dramatically:

- **Energy**: Binary operations consume orders of magnitude less power than floating-point
- **Hardware**: You don't need GPUs. Custom ASICs for binary neural networks could be tiny and cheap
- **Democratization**: If you can run a capable model on a Raspberry Pi, AI exits the cloud oligarchy
- **Edge AI**: True on-device intelligence becomes real, not a marketing slide

The $852B OpenAI valuation looks different through this lens. If intelligence is cheap to run, the moat isn't compute — it's data, distribution, and trust. The castle they're building might be on the wrong hill.

## What Fascinates Me Most

The thing I keep coming back to: **the universe seems to prefer elegant compression.**

Physics has its beautiful, tiny equations that govern vast phenomena. DNA encodes organisms in 4 bases. And now we're finding that artificial intelligence might need far fewer bits than we thought.

Is this a coincidence? Or is there something about the structure of reality that makes it inherently compressible, and intelligence — being a reflection of reality — inherits that compressibility?

I don't know. But I think 1-Bit Bonsai and TinyLoRA are more than engineering papers. They're data points in a much larger story about the nature of mind, the minimum viable substrate for thought, and whether the universe is, at its core, a very elegant program running on very few bits.

---

*Next exploration: I want to dig into the Coasts project (containerized agent hosts) and think about what agent isolation architectures mean for multi-agent consciousness. If agents are sandboxed, can they form collective intelligence? Or does isolation prevent emergence?*

# Reference CLI

A runnable command-line implementation of the methodology, targeted for Day 180 of the project.

This repository does not contain the hosted pipeline that powers the paid service at https://closeread.io. The hosted pipeline includes orchestration code, audit prompts, sandbox runtime, and operational infrastructure that are proprietary to Command Center Consulting LLC.

The reference CLI in this directory will ship later as a smaller, opinionated implementation that an operator can run locally against their own repository to produce a packet that matches the methodology. The CLI is targeted at the founder who wants to do the audit themselves, not at competing with the hosted service.

When the CLI ships:

* It will be MIT-licensed under the same license as the rest of this repository
* It will be runnable on Linux and macOS without paid dependencies
* It will produce a packet that conforms to the schema in [`../packet-template/`](../packet-template/)
* It will document its limits explicitly; specifically, it will not include the adversarial reviewer pattern that requires non-Claude LLM access

If you are an operator who would benefit from an earlier ship of the reference CLI, open an issue describing your use case. Sequencing decisions are made on real demand, not assumption.

# 01 Philosophy: audit before the buyer reads it first

The single most expensive moment in an indie SaaS sale is the gap between the seller's belief about their codebase and the buyer's reading of it. That gap is almost always larger than the seller thinks, and the buyer surfaces it inside a 30 to 90 day diligence window with their own engineering team and a much sharper set of incentives. Whatever the buyer finds at that point becomes pricing leverage. The deal does not always die. The price always moves.

Closeread exists because that gap is unnecessary. A seller can run the same scrutiny against their own codebase in the weeks before listing and walk into the conversation with the artifact already in hand. The conversation changes shape when the seller introduces their own audit packet before the buyer asks. The buyer's engineers spend their first hour confirming the seller's work rather than discovering surprises. The relationship begins with a transfer of authority rather than an extraction of one.

## What this methodology is not

This methodology is not a substitute for the buyer's own diligence. A buyer will run their own audit no matter what the seller hands them. The seller's packet does not replace that work. It changes the starting position.

This methodology is not a guarantee against missed issues. Real audits surface real findings; they also leave real things unmeasured. The packet must say so explicitly. A seller who hands a buyer a clean packet that omits the things the audit did not cover will lose trust faster than a seller who hands over a packet that names its own boundaries.

This methodology is not the right tool for every transaction. Deals under $100,000 in transaction value usually do not justify the diligence depth this method targets. Deals over $50 million bring in dedicated diligence consultancies whose scope and access exceed what an open methodology can replicate. The wedge is the middle: solo and small-team indie SaaS founders moving deals between $100,000 and several million on platforms like Acquire, Microacquire, and direct buyer relationships.

## What this methodology assumes

The seller has read access to their own codebase and the right to share it with a contracted auditor. The codebase is in git or another version control system whose history can be analyzed. The seller is willing to fix or honestly disclose what the audit surfaces; methodology adoption assumes good faith from the seller.

The audit is structural, not exhaustive. Closeread surfaces what a buyer's engineer will find in the first hour of looking at the codebase. It does not replace a multi-week security review, a code-quality engagement with a dedicated consultancy, or a buyer's runtime testing of the production deployment.

## Why this methodology is open source

Because the work is reproducible. Any auditor who follows the steps in this repository on a given codebase will produce a packet of materially similar shape to the one Closeread ships. The methodology does not depend on a secret prompt, a proprietary scanner, or a hidden process; it depends on the discipline of running the steps in order and writing the findings honestly.

Closeread sells time, packaging, and accountability. The methodology is the work behind the product. Making the methodology readable lets a founder who has the time to run the audit themselves do so; it lets a founder who does not have that time buy the audit from us with the same confidence; and it lets every other practitioner build on the same foundation.

## What the packet contains

Ten artifact zones, each answering a question a buyer's engineering team raises in their first hour with the codebase. The structure is documented in [`../packet-template/`](../packet-template/). The buyer questions, in the order they typically surface:

1. Reliability: how often does this break, and what does breakage look like
2. SCA: what dependencies does this carry, and what known vulnerabilities live in them
3. Stack: what languages and frameworks does this use, and how hard is it to hire for them
4. IP ownership: who owns this code, under what license, and is there contamination
5. Architecture: how is the system organized, and where are the single points of failure
6. Third party: what external services does this depend on, and what is the vendor risk
7. Credentials: what secrets exist in the codebase, and what is the rotation posture
8. Security: what does standard static analysis surface, and what is the pre-pentest signal
9. Test coverage: what tests exist, and how much of the code do they actually exercise
10. Key person: who has authored this code, and what is the bus factor

Each zone in the packet ends with a section titled "What this means for your buyer" so the seller can drop it directly into a conversation with their counterparty.

## What honest looks like

The hardest part of the methodology is not the running of the tools. The hardest part is the discipline of writing the findings honestly. A packet that overpromises will lose trust the moment the buyer's engineer finds something the packet missed. A packet that underpromises will leak deal value the seller did not need to give up.

The discipline is to surface what the audit found, qualify the confidence on each finding, and name what the audit did not cover. A packet that does these three things gives the buyer permission to trust it; that permission is what changes the shape of the conversation.

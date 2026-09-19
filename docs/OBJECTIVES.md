# MacroTrading — objectives for a complete portfolio-management system

## Purpose of this document

This document defines the intended purpose, capabilities and outcomes of MacroTrading. It is a standalone brief that another LLM, product team or developer can use to design a system from first principles.

It does not prescribe a technology stack, architecture, data provider, AI model, scoring formula, investment strategy, risk thresholds or execution mechanism. It does not describe the completion status of an existing implementation. Those choices must serve the objectives below and be made explicitly during system design.

## 1. Core objective

Create a comprehensive, continuous portfolio-management system that helps a portfolio manager understand markets, generate investment ideas, recommend trades, decide what to do and at what size, build a portfolio, and manage that portfolio as conditions change.

The system must connect the full investment process: market assessment, themes, trade implementation, portfolio construction, monitoring, risk management and decision review. Every subsequent recommendation must take account of the portfolio that actually exists, the user's outstanding intentions and decisions, and the latest available information.

The portfolio manager retains ownership of investment decisions and chosen sizes. The system supplies analysis, alternatives, recommendations and a durable record of the reasoning and actions.

## 2. The questions the system should help answer

- What is happening in markets, and what has changed since the previous review?
- Which themes and opportunities are emerging, strengthening, weakening or becoming invalid?
- Which trades could express those views, and why choose one expression over another?
- How would a proposed trade and the size I want affect my existing portfolio?
- What have I decided to do, what remains pending, and what has actually been implemented?
- What do I own now, what risks am I running, and where do positions reinforce or offset one another?
- Should I hold, add, take profit, reduce risk, hedge, change an expression or exit?
- What should I review next, and which changes would cause me to reconsider a decision?
- What can I learn from the decisions I made, deferred or rejected?

## 3. The continuous management cycle

| Stage | Objective | Required outcome |
| --- | --- | --- |
| Understand markets | Form and update a coherent assessment of the relevant market environment | A dated view of conditions, changes, drivers and uncertainty |
| Develop themes | Identify and challenge investment hypotheses | Themes with supporting evidence, counterarguments, catalysts and invalidation conditions |
| Recommend trades | Translate themes into possible market expressions | Actionable alternatives, their rationale, relevant economics and portfolio implications |
| Record user decisions | Capture what the manager wants to do, including size and conditions | A clear distinction between recommendations, chosen actions, deferred ideas and rejected ideas |
| Build and update the portfolio | Reflect what has actually been implemented and changed | An accurate current portfolio, with pending activity visible separately |
| Monitor positions and risk | Reassess investment theses, performance and aggregate exposure | An explanation of what changed and what needs attention |
| Recommend management actions | Propose how to manage existing positions and the portfolio as a whole | Prioritized recommendations to hold, add, take profit, reduce, hedge, replace or exit |
| Review outcomes | Compare decisions, implementation and subsequent developments | Lessons that inform future market assessments and decisions |

This cycle continues throughout the life of the portfolio. New information can initiate a review at any stage. An existing position can lead to a hedge idea; a changed thesis can lead to an exit; a newly attractive trade can require reducing another position first.

Continuity means maintaining context and reassessing it over time. The choice of update frequency and how reviews are initiated belongs to system design and the manager's operating needs.

## 4. Market assessment and idea generation

The system should organize relevant market, economic, policy, research and other information into a coherent investment context. It should identify material changes and distinguish observed information from forecasts, interpretations and unresolved questions.

Themes must be understandable investment hypotheses. Each should explain the proposed economic mechanism, why it matters, what could make the view correct or incorrect, the relevant time horizon, and the developments worth monitoring. The system should make competing explanations and contradictory evidence visible.

Idea generation should consider both opportunities in the market and the portfolio manager's current situation. A new idea may improve expected outcomes, diversify existing exposure, address a vulnerability, or offer a better expression of an existing view. The system should also be able to conclude that no action is currently justified.

The relevant asset classes and instruments should follow the investment mandate and the economics of the theme. The objectives should support multi-asset portfolios and trades with multiple legs where appropriate, without imposing a fixed instrument universe.

## 5. Trade recommendations and implementation choices

For a proposed trade, the system should explain, where relevant and supported by available information:

- The investment thesis and the evidence or change that motivates acting now.
- The instrument or combination of instruments, direction and intended exposure.
- Alternative ways to express the same view and the trade-offs between them.
- The proposed entry conditions, investment horizon and conditions for reassessment.
- The potential sources of return, downside and uncertainty.
- Relevant costs, liquidity, carry, financing, cash or balance-sheet use and implementation constraints.
- The effect on the current portfolio, including concentrations, overlapping exposures and existing hedges.
- What would justify adding, taking profit, reducing, hedging or exiting later.

Recommendations must be distinguishable from instructions already approved by the manager. Missing inputs must remain visible; the system should identify what is needed to make a recommendation actionable rather than manufacture precision.

The system should help compare potential sizes against the manager's objectives and constraints. Where justified, it may propose sizes, ranges or alternatives with an explanation. It must capture the size the user actually chooses and assess that choice, including any difference from the recommendation. The size unit should suit the trade and be clear to the user.

## 6. Decisions, intentions and implementation tracking

The system must maintain an ongoing record of the manager's decisions, including acceptance, modification, deferral, rejection and a deliberate decision to make no change.

For each material decision, retain the associated idea or position, the recommendation considered, the user's reasoning, chosen size, conditions and timing, and the information available at that point. Later amendments should preserve the earlier rationale so that the evolution of the decision can be understood.

The system must distinguish:

- What the system recommended.
- What the manager intended or authorized.
- What is pending, partially implemented, cancelled or no longer appropriate.
- What was actually implemented.
- What remains to be done or reviewed.

An approved intention must not be represented as an existing holding before implementation is confirmed. Differences between the intended and implemented position should be visible, including size, timing, price or missing legs when those are relevant.

The mechanism for implementing and confirming actions is a design choice. Whatever mechanism is selected, it must preserve a reliable connection between the decision and the resulting portfolio change.

## 7. Portfolio construction and current state

The system must enable a manager to start a portfolio or bring an existing portfolio into the process, then maintain it throughout its life.

The current state should include the holdings, cash and other economically relevant balances, valuations, profit and loss, exposures and constraints needed to support decisions. Pending intentions and actions should remain visible alongside the actual portfolio without being confused with it.

Updates should reflect new trades, additions, reductions, exits, hedges and relevant changes in prices, currencies, costs or instrument economics. Discrepancies and missing information must be surfaced so the manager can understand how reliable the displayed state is.

Positions should remain connected to their originating themes and decisions, while allowing their purpose to evolve. A position may support more than one theme or hedge several exposures. A hedge should have an explicit purpose and be reviewed as that purpose changes.

Portfolio construction must consider the combined portfolio. A trade can be attractive on its own while creating excessive overlap, funding pressure or an undesirable aggregate exposure. The system should compare the current portfolio with plausible portfolios after proposed actions, including combinations of actions where their interaction matters.

## 8. Ongoing monitoring and risk management

Monitoring should cover both investment reasoning and portfolio economics. It should identify changes in the thesis, catalysts, market conditions, valuation, performance, liquidity, financing and relevant risk exposures.

The system should help the manager understand risk at the position, theme and total-portfolio levels using measures appropriate to the mandate and instruments. It should make concentrations, common drivers, offsets, hedge effectiveness and material scenarios understandable. It must not require a single risk measure to describe every strategy.

Each review should distinguish changes caused by market developments from changes caused by the manager's actions or corrections to the underlying portfolio information. It should identify what needs a decision, why it matters and the consequences of leaving the portfolio unchanged.

Alerts and reviews should support attention and action. Material new information should update an existing recommendation or create a linked reassessment, preserving the record of what was previously recommended and why.

## 9. Recommendations for managing existing positions

The system should produce reasoned management recommendations using the current portfolio, the original and evolving thesis, the manager's decisions, and updated market information.

| Action | Question the recommendation should address |
| --- | --- |
| Hold | Does the thesis and portfolio role still justify maintaining the position? |
| Add | Has the opportunity improved sufficiently to justify more exposure within the portfolio's constraints? |
| Take profit | Has the opportunity been realized, the remaining reward diminished, or the position become too large after gains? |
| Reduce risk | Which reduction would address the identified vulnerability, and what investment exposure would be lost? |
| Hedge | Which protection best addresses the identified risk, at what cost and with what residual exposure? |
| Replace or restructure | Is there a better instrument, combination or expression for the intended exposure? |
| Exit | Has the thesis failed, the horizon expired, the implementation become unattractive, or the position lost its portfolio purpose? |

Recommendations should state why action is proposed now, the relevant position or portfolio exposure, the contemplated change in size, the expected effect, costs and disadvantages, alternatives, and conditions for review. Where practical, compare the recommendation with taking no action.

Profit-taking must account for the remaining opportunity and portfolio context. Hedging must identify the risk being hedged, the degree and duration of intended protection, the cost, and risks left behind or introduced. Risk reduction may involve a coordinated change across several positions rather than treating each holding in isolation.

The manager can accept, modify, defer or reject a recommendation. The resulting decision and any eventual implementation must feed back into the next assessment. A recommendation that relies on an outdated portfolio state must be reconsidered before it is acted upon.

## 10. Decision review and learning

The system should make it possible to reconstruct the sequence from market view to recommendation, decision, implementation, subsequent reviews and outcome.

Review should help distinguish the quality of the original reasoning, the chosen expression and size, implementation effects, subsequent management actions and external market developments. A profitable outcome alone does not establish that a decision was well founded, and a loss alone does not establish that the process was poor.

The manager should be able to examine patterns in accepted, modified, deferred and rejected ideas and use those observations to improve future decisions. Historical judgments must use the information available at the time, with hindsight clearly separated.

## 11. Usability and trust

The manager should be able to see the current portfolio, material changes, priority recommendations, pending decisions and next review points without reconstructing them from disconnected reports.

Analysis should be explainable and traceable to the information, portfolio state and assumptions used. Uncertainty, missing or stale information, conflicting evidence and consequential limitations should be presented where they affect a decision.

The system should let the manager explore alternatives, revise intentions and record judgment throughout the process. It should support changing mandates, investment universes, constraints and portfolio-management styles without imposing an undocumented investment philosophy.

Human review should be proportionate to the action. The central requirement is that recommendations, user authorization and actual portfolio changes remain distinguishable and accountable.

## 12. Success criteria

A system fulfills these objectives when a portfolio manager can complete the following journeys and understand the state at every step:

1. Identify an emerging theme, examine competing evidence, compare trade expressions and record a chosen action and size.
2. Start a portfolio or establish the state of an existing one, implement a decision and see the resulting holdings and risk.
3. Revisit the portfolio after market changes and receive an explanation of what changed and which decisions require attention.
4. Assess a recommendation to take profit or reduce exposure, choose a different size if desired, implement it and retain the full decision history.
5. Identify a portfolio vulnerability, compare hedging alternatives and understand both the protection and residual risks after the selected action.
6. Distinguish pending or partially implemented intentions from actual holdings and avoid counting the same action twice.
7. Defer or reject an idea, retain the reasoning and revisit it when the relevant conditions change.
8. Reconstruct why a position exists, how its size evolved, which recommendations were followed and what subsequently happened.

The defining outcome is a continuous, coherent investment-management process in which market understanding, recommendations, decisions, portfolio state and risk management remain connected over time.

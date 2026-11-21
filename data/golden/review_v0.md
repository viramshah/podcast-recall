# Golden set v0: review sheet (generated)

Regenerate with the script that wrote it, or read any item with `uv run podcast-recall eval show <id>`.

## How to review (about 3 hours)

For each question, decide: **keep**, **edit** or **replace**. Check four things:

1. **Would you really ask this?** Natural wording, not copied from the transcript. If not, rewrite it in your words.

2. **Is the gold answer right and complete?** Read the transcript text under it (and open the link if unsure). Fix the gold answer, or the time, in `data/golden/golden_v0.csv`.

3. **Is the time inside the answer?** The link opens at the gold time. For a who/when question, the answer must be at that time.

4. **For the unanswerable, false-premise and not-in-library types:** is the answer truly absent from the library (or present only in a held-out episode)? `eval check` searches for the phrases listed.

**Your own questions:** at least a third of the final set (20 of 60) should be ones you write from memory. Replace a drafted question of the same type with yours, set `author` to `pm`, and keep the type counts (20 / 13 / 10 / 7 / 5 / 5). Questions you author from episodes in the library need `gold_evidence` as `video_id@mm:ss`.

Split: **dev** items may be used for tuning later; **heldout** items are only for the final gate. Don't use heldout items to tune anything.


## Single-fact lookup (20)

### n01: How does the US debt burden compare with Japan's, according to Gita Gopinath?
- Split: heldout `raj`  |  Author: agent_reviewer
- **Gold answer:** She says the US is not the most indebted large economy: Japan's debt is about 230% of GDP against about 100% for US federal debt. She adds that the absolute size of the debt is less interesting than its size relative to the economy.
- Key points: Japan about 230% of GDP; US federal about 100%; size relative to economy matters
- Evidence: [Ex-IMF Chief Economist: How USA Debt Triggers a Global Crisi at 18:19](https://youtu.be/dNIef2fGLQY?t=1099)
  > So, first of all, it's not the country with the most amount of debt. the country among the large economies that have very high levels of debt, Japan is the highest. So Japan's debt to GDP is around 230%. The US federal debt to GDP is around 100%. But the absolute number of the US

### p01: What was the first NotebookLM podcast demo Josh Woodward remembers hearing, and why did it grab him?
- Split: dev  |  Author: pm_proxy
- **Gold answer:** Two people on the team played him AI hosts discussing the proceedings of the British Parliament debates, dry material that the AI hosts made genuinely interesting. That was when the team decided they had to do something with it.
- Key points: British Parliament debates; two AI hosts; made dull material interesting
- Evidence: [Why every company now needs to think and operate like a lab  at 13:27](https://youtu.be/3I6QYkccd3o?t=807)
  > Is there a great example or story of a product that emerged in this way? Yeah, I mean, I remember still the first time I heard the first, like, Notebook LM podcast. Exactly where I was standing. It was right outside this room. Yeah. And it was probably at like 6.30 p.m. on a Tuesday

### p02: In the beginner agents course, what's the difference between a global skill and a project-level skill?
- Split: dev  |  Author: pm_proxy
- **Gold answer:** A global skill applies to every project and session (his example is a 'truncate' skill he wants everywhere), while a project-level skill lives in one project only (his Sebastian-referral skill would just clog the head-of-marketing project's context). The same global versus project split applies to CLAUDE.md files and MCPs.
- Key points: global skills apply to every project; project skills only in one project; avoid clogging context; same for CLAUDE.md and MCPs
- Evidence: [AI Agents Full Course 59 Minutes (for beginners) at 56:52](https://youtu.be/eA9Zf2-qYYM?t=3412)
  > I'll just go over super quick so like those skills for example you can add them at a global level which means they apply to every single project you work in whether it's the executive assistant you're head of marketing and some skills you want globally because you might use them in every chat like

### p03: How does Rob Snyder say to stop customers from churning right after they buy?
- Split: dev  |  Author: pm_proxy
- **Gold answer:** He says everyone who buys is guaranteed to churn until some milestone 'X', so you find the leading indicator after which churning would be weird (like a Slack team hitting a message-count threshold) and design onboarding as a 'bullet train' that gets every customer there. At his restaurant-software startup, getting a notification about a preventable quitter in the first two weeks after purchase was that milestone.
- Key points: everyone churns until X; find the leading indicator of retention; Slack message count example; design onboarding to get every customer there
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 1:07:31](https://youtu.be/19qrLchbQEc?t=4051)
  > And so the way I think about like delivery post-sale is that basically everybody who buys is guaranteed to churn until X. In which case they're weird to churn. And all delivery is all, everything is about figuring out what is X and how do you design a bullet train so every customer gets there.

### p04: What bounce rate did Sachin Puri say should worry a small business owner about their website?
- Split: dev `raj`  |  Author: pm_proxy
- **Gold answer:** He says if your bounce rate is more than 50%, meaning visitors open a page and leave without going to any other page, you should go and check right away. Losing half your visitors that way means you have a problem, which is why the hero image and tagline must make it clear they are in the right place.
- Key points: bounce rate above 50%; check right away; clear hero image and tagline
- Evidence: [Billion-Dollar Tech CEO: How To Make AI Work Like 100 Employ at 34:50](https://youtu.be/8ol3j7o1U7o?t=2090)
  > people know they have come to the right place. Okay. Because the bounce rate can kill your website. If your bounce rate is more than 50, you should go and check right away. If your bounce rate is the people who come into your page and bounce without going to any other page, they just

### p05: What LinkedIn acceptance rate does Rob Snyder say you should be hitting when you reach out to prospects?
- Split: heldout  |  Author: pm_proxy
- **Gold answer:** If you send around 100 to 150 connection requests a week, he aims for 30 to 40 percent to accept, and then 30 to 50 percent of those should reply. If you are below that, your profile or your message is not interesting enough.
- Key points: 30 to 40 percent accept; 30 to 50 percent reply; low rates mean profile or message is not interesting
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 39:44](https://youtu.be/19qrLchbQEc?t=2384)
  > Go for that. Add 20 a day. And then message them when they accept the connection request. And if you're sending, like if you're connecting with, I don't know, let's say you connect with 100 people per week or you send 150. My typical targets for that are like 30 to 40% of them should

### p06: Who does Jen Abel say should be reaching out to a C-level exec at a big company, and why not just a marketing campaign?
- Split: heldout  |  Author: pm_proxy
- **Gold answer:** She says most C-level executives don't respond to marketing, they respond one-on-one, and the best person for that is the founder, even at a Series B or C company. The founder should be eager to get in front of that executive.
- Key points: C-level execs do not respond to marketing; respond one-on-one; the founder is best placed
- Evidence: [How to close $100K+ enterprise deals, step by step | Jen Abe at 11:30](https://youtu.be/YS9In813jJ0?t=690)
  > Most C-level executives don't respond to marketing. They might see your brand. They're not going to respond to a marketing campaign. They will respond one-on-one. And the best individual to one-on-one to a corporate executive is the founder. Even if you're a Series B, Series C. Right. It is the founder should be ecstatic to

### r01: Besides marketing, what else does Rob Snyder say a customer case study is useful for?
- Split: heldout  |  Author: claude
- **Gold answer:** He says a case study can be used to qualify and disqualify prospects, and to help people understand what you do: you can tell a prospect they do not look like your case study, so it would be a lot of work and might not be a good fit.
- Key points: qualification; disqualification; helps people understand what you do
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 1:15:27](https://youtu.be/19qrLchbQEc?t=4527)
  > And you can use it for qualification, disqualification, and for people to understand what you do. That's, that's funny. There's this whole theme now of building software factories, um, where, you know, product build itself, but, um, there's a really another version of a factory you're building, which is even the broader version of just

### sf01: What can push inflation away from a central bank's target, according to the guest?
- Split: dev `raj`  |  Author: claude
- **Gold answer:** A surge in demand in the economy (for example from a large inflow of foreign money), or government programmes that add to demand.
- Key points: demand boom; foreign money inflows; government programmes
- Evidence: [Ex-IMF Chief Economist: How USA Debt Triggers a Global Crisi at 10:30](https://youtu.be/dNIef2fGLQY?t=630)
  > is, what can generate inflation deviating from target? It could be that there is so much of a boom in demand in the economy now for multiple reasons, including, say, you're getting a lot of infusion of foreign money, multiple reasons for it. There's a big increase in demand or the government, which is very

### sf02: What was the IMF originally created to be, and what test decides whether it lends to a country?
- Split: heldout `raj`  |  Author: claude
- **Gold answer:** It was created to be a financial firefighter. It lends if it has confidence that the country's new government will move the country away from the abyss.
- Key points: financial firefighter; confidence in policies
- Evidence: [Ex-IMF Chief Economist: How USA Debt Triggers a Global Crisi at 1:10:51](https://youtu.be/dNIef2fGLQY?t=4251)
  > The decision about whether you lend to a country or not is whether you have confidence that the policies that this new government, by the way, whoever is going to be in power, will be able to move the country away from the abbess. That's always the test. Nobody ever has defaulted to the IMF,

### sf03: Which questions does the guest suggest putting to an AI assistant to find channel partners for a product?
- Split: dev `raj`  |  Author: claude
- **Gold answer:** Which markets the product is used in, who the customers are, and through which channels they get access to such services; then ask for a profile of 10 to 20 companies.
- Key points: markets; customers; channels; profile 10-20 companies
- Evidence: [Billion-Dollar Tech CEO: How To Make AI Work Like 100 Employ at 1:06:36](https://youtu.be/8ol3j7o1U7o?t=3996)
  > what are the top markets in which this product has been used? Who are the customers who are using this? Okay. What are the different channels through which they are getting access to these services? Give me the names of, build me a full profile of 10, 20 people, companies in each of those markets

### sf05: What does Vinh Giang give as the first step to communicating better?
- Split: heldout `raj`  |  Author: claude
- **Gold answer:** Become self-aware: you have never seen yourself communicate, and your view of how you come across is not accurate.
- Key points: self-awareness; your view is not accurate
- Evidence: [Why Your Communication Makes People Ignore You & How To Fix  at 14:40](https://youtu.be/BgeNDG5jD60?t=880)
  > I would say the first thing is let's become self-aware. All right. You've never seen yourself communicate to somebody else. You have a view of how you think you communicate. It's not accurate, right? Unless you're a content creator, unless you're watching your videos back, unless you do podcasts all the time, which most people

### sf06: In what situations does Vinh Giang say you should write down a story you might tell later?
- Split: dev `raj`  |  Author: claude
- **Gold answer:** Whenever something emotionally moves you, grab your phone and document it straight away; the biggest rule of storytelling is to document.
- Key points: document when emotionally moved; use your phone
- Evidence: [Why Your Communication Makes People Ignore You & How To Fix  at 1:11:39](https://youtu.be/BgeNDG5jD60?t=4299)
  > do you document? Document when something emotionally moves you. anytime something emotionally moves you document it from this point in life right now where you are in life the moment you feel a strong emotion with something something that happened to you during that day or that week grab your phone out document it and

### sf07: Where does Josh Woodward say the best new product ideas at Labs actually come from?
- Split: dev  |  Author: claude
- **Gold answer:** Rarely from design sprints or scheduled idea sessions. They come when people are hacking and building on their own, in the hallway, on weekends or over a break, and then share a video.
- Key points: not design sprints; hacking on weekends and breaks
- Evidence: [Why every company now needs to think and operate like a lab  at 6:19](https://youtu.be/3I6QYkccd3o?t=379)
  > They very rarely, at least in my experience, have come from design sprints or times where you set aside on a calendar, okay, this is, we're going to go come up with our next idea. They usually come When people are swimming in the hallway, maybe on a weekend, often over a break, a lot

### sf09: How often does the guest tell a prospect that the gap between them is simply too big?
- Split: dev  |  Author: claude
- **Gold answer:** About one in every four calls. In two to three of every four there is something real.
- Key points: one in four calls; revisit in a year
- Evidence: [How to close $100K+ enterprise deals, step by step | Jen Abe at 25:44](https://youtu.be/YS9In813jJ0?t=1544)
  > Yeah, there's something real. One out of every four calls, I'm like, listen, based off of the maturity of where you guys are and where we are, it's too much of a gap. Like, I'd love to revisit this in a year, like once you guys have a chance to like solve for X, Y,

### sf10: How should a software price relate to the length of the sales cycle, in the guest's view?
- Split: dev  |  Author: claude
- **Gold answer:** Price should be based on the sales cycle: if you can close in 90 days for 100K, do that every time; a deal that takes nine months should be priced higher.
- Key points: price follows sales cycle; 90 days for 100K
- Evidence: [How to close $100K+ enterprise deals, step by step | Jen Abe at 59:37](https://youtu.be/YS9In813jJ0?t=3577)
  > Your price should be predicated on your sales cycle, right? Like if you can get a deal done in 90 days for 100K, do that all the time, right? If it takes nine months to get a deal done, you probably should be charging 250, 300K. What are your thoughts on forward deployed engineers as

### sf12: What does Rob Snyder mean by a hair-on-fire problem?
- Split: dev  |  Author: claude
- **Gold answer:** An urgent, concretely defined problem, such as a to-do that your boss is waiting for and that must happen now.
- Key points: urgent; concrete; must happen now
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 8:43](https://youtu.be/19qrLchbQEc?t=523)
  > And this is an urgent problem. So in a sense, this is the hair on fire problem, very concretely defined. Here's what hair on fire looks like. I have like a to-do my boss is waiting for me to do, and it needs to happen now. It's not just like a general thing that I

### sf13: What kind of reaction from a prospect shows genuine interest, and what shows only polite interest?
- Split: heldout  |  Author: claude
- **Gold answer:** Leaning in ('wait, you can do what?' or 'I will pay you right now') is the signal. Leaned-out enthusiasm ('tell me more', 'send some information for the team to review') is not worth chasing.
- Key points: leaning in vs leaned out
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 25:51](https://youtu.be/19qrLchbQEc?t=1551)
  > What you're looking for as well as they're leaning in. Wait a second, you can do what? What you're not looking for is kind of like leaned out enthusiasm. Okay. Well, tell me more. Well, let me, yeah, we'll, we'll think about it. Can you send more information so our team can review that? Like,

### sf14: What is an agent harness, as explained in the course?
- Split: dev  |  Author: claude
- **Gold answer:** The platform that runs the loop: a model that keeps going until the task is done, connected to your tools and your context. Popular agent products are agent harnesses.
- Key points: loop until done; tools and context; popular agents are harnesses
- Evidence: [AI Agents Full Course 59 Minutes (for beginners) at 6:21](https://youtu.be/eA9Zf2-qYYM?t=381)
  > facilitates this process and basically facilitates this loop to happen is known as an agent harness. And all of the popular AI agent platforms on the market that you'd be familiar with are just agent harnesses. They're just applications where this loop is facilitated. And I want to actually run this little prompt I prepared

### sf15: In the beginner's AI agents course, how is a skill different from keeping something in an agent's memory?
- Split: dev  |  Author: claude
- **Gold answer:** A skill packages a whole process as a markdown file (for example writing a proposal) so it is done the same way each time; memory holds preferences and facts. Process material clogs memory and belongs in skills.
- Key points: skill = packaged process; memory = preferences
- Evidence: [AI Agents Full Course 59 Minutes (for beginners) at 41:25](https://youtu.be/eA9Zf2-qYYM?t=2485)
  > basically it packages up that process into a dot skill file and in that dot skill file it's basically just a marked down file that explains the exact process that you went through so you could create a proposal skill and then every time you now you need a proposal written it just takes that


## Cross-episode synthesis (13)

### n06: What do the guests suggest for learning directly from customers what they want or why they bought?
- Split: dev `raj`  |  Author: agent_reviewer
- **Gold answer:** Sachin Puri suggests surveying buyers and, if you only have a handful, calling them to ask how they found you and why they chose you. Rob Snyder describes a company whose working product ideas all came from customers asking for something extra in sales calls, and advises talking to about five existing customers to look for pull.
- Key points: survey buyers; call customers; how did you find us; ideas from sales calls; talk to five customers
- Evidence: [Billion-Dollar Tech CEO: How To Make AI Work Like 100 Employ at 1:01:59](https://youtu.be/8ol3j7o1U7o?t=3719)
  > thing first who is this customer why did they buy their product where do i find that out how do i like somebody just bought something from my website how do i find that survey put a survey put a survey and if you have only handful of the customers just give them a call
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 1:18:10](https://youtu.be/19qrLchbQEc?t=4690)
  > I can't share the name, but a company was, a new product leader at a company was telling me, hey, yeah, the way we get our ideas, all of the ideas that have worked have come from sales calls where they said, cool, yeah, you can do X, but could you also do this other

### n07: What do the guests say to do when early evidence shows an idea is not working?
- Split: dev  |  Author: agent_reviewer
- **Gold answer:** Josh Woodward describes a Gemini feature whose early data was weak, where a PM said it should not launch; he praised her and says that when the team says it is not going, the answer is to pivot. Rob Snyder says that if five calls show no pull you ask a 'Hail Mary' question about anything on their to-do list, then do another set of five calls with a new pull hypothesis or go back for hands-on knowledge.
- Key points: early data weak; PM said do not launch; pivot; no pull after five calls; Hail Mary question; new pull hypothesis
- Evidence: [Why every company now needs to think and operate like a lab  at 18:51](https://youtu.be/3I6QYkccd3o?t=1131)
  > and be able to say like, hey, I don't think this is working. And yesterday, just as an example, we had a feature we were really excited about in Gemini we were gonna launch and we got some of the early data back. People went out, looked in the eyes and it just wasn't there.
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 1:05:54](https://youtu.be/19qrLchbQEc?t=3954)
  > go hands, hands on with some other small business sort of thing? Or what do you recommend? Yeah. So different pathways there. Hopefully you've asked the hail Mary question and you've learned something. That's like worth double clicking into. And the Hail Mary question is just like, what is there anything that we can do

### n09: What do the guests say about doing work for free to win a customer?
- Split: dev  |  Author: agent_reviewer
- **Gold answer:** Rob Snyder advises against free design partnerships because they lead to products that do not sell. The speaker in the $1M solo business episode suggests a free case study for, say, a dental clinic in exchange for introductions to three colleagues, and Jen Abel prefers to forgo money for a short two-to-three-day pilot to control the sales cycle, while charging for longer ones.
- Key points: no free design partnerships; free case study for introductions; two-to-three-day pilot; charge for longer pilots
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 58:35](https://youtu.be/19qrLchbQEc?t=3515)
  > I imagine your advice here, just like sell it directly. Don't try to give them for free. Don't set up some kind of partnership thing. Yeah. Why shoot yourself in the foot? And again, the reason not to is because you find it doesn't lead to the best, to stuff that actually sells and works,
- Evidence: [The $1M+ Solo Grok Bot Business (Full Course) at 44:38](https://youtu.be/67BmkptgTms?t=2678)
  > Yeah. Couldn't agree more. The one thing I'd add is if you are going to go and do a free case study for someone, say a dental clinic, one thing you can do is you can say, hey, I normally charge $50,000 a year for this service. I'm going to do this for you for
- Evidence: [How to close $100K+ enterprise deals, step by step | Jen Abe at 49:25](https://youtu.be/YS9In813jJ0?t=2965)
  > They're not the user. Who are the users of this? I want them to experience the magic and the power of what this is. You could charge them for a pilot if it's an extended period of time, but I'd rather forego the money and do a two to three day pilot so that at

### p07: How should I decide which niche or customer group to go after?
- Split: dev  |  Author: pm_proxy
- **Gold answer:** In the solo Grok Bot business episode the guest says not to pick a niche up front: call about 50 people you know, do the first project for free as a case study, and let the industry that emerges decide it. In the agent-harness episode the advice is to 'marry the niche, date the product', meaning fall in love with who you serve because the product will keep changing.
- Key points: do not pick niche first; call 50 people you know; first project free as case study; marry the niche, date the product
- Evidence: [The $1M+ Solo Grok Bot Business (Full Course) at 41:04](https://youtu.be/67BmkptgTms?t=2464)
  > Yeah. So the biggest thing is like deciding your niche is, I think, a very difficult problem for a lot of people. And when people get started in business, here's a common thing that happens. You'll get super amped up. You'll say, okay, you know what? I'm going to start. I'm going to make an
- Evidence: [Stop building AI wrappers. Start building agent harnesses. at 48:35](https://youtu.be/st61aKW8P5A?t=2915)
  > I think like if you're, if you're choosing a startup idea or choosing a business, I always say like, I'm going to, marry the niche, date the product. I love that. Fall in love with who you're trying to serve. Yeah, yeah. Because we live in an age where you're going to be iterating on

### p08: Do the guests think a human should still stay in the loop when AI agents do creative or design work?
- Split: dev  |  Author: pm_proxy
- **Gold answer:** Yes. The agent-harness guest says subjective work, where two people disagree on what good looks like, needs a human in the loop. The Grok Bot guest says never go straight to the output and that his own approval on design and functionality is necessary, because his feedback is what lets the AI work better.
- Key points: subjective work needs a human in the loop; judgment calls; do not go straight to output; own approval on design and function
- Evidence: [Stop building AI wrappers. Start building agent harnesses. at 9:06](https://youtu.be/st61aKW8P5A?t=546)
  > In our case, what makes it different is that it's very subjective. There's a lot of judgment calls to make along the way where two different people will disagree about what good looks like, which means you want to have the human in the loop. And also where the person using it actually really cares
- Evidence: [I'm Obsessed With Grok Bot. Here's Why at 27:24](https://youtu.be/1cWZ7Ekff6E?t=1644)
  > And the thing is, I'm genuinely a user of all these tools. And to your point, you never want to go directly to output, right? You want to like, I'm still a big believer in human in the loop when it makes sense. And in terms of design, my approval is 100% necessary. In terms

### p09: Should you show a demo on the very first sales call?
- Split: heldout  |  Author: pm_proxy
- **Gold answer:** Jen Abel says no: for the first call, show no demo and no slides, just have a one-on-one dialogue for 30 minutes. Rob Snyder also makes it a 30 minute call and is iffy on a demo, since early on you probably have none, though later you might include a very short one.
- Key points: no demo or slides on first call; 30 minute conversation; early stage may have no demo to show; maybe a very short demo later
- Evidence: [How to close $100K+ enterprise deals, step by step | Jen Abe at 19:22](https://youtu.be/YS9In813jJ0?t=1162)
  > And this is what I like to do. Super informal. Don't show them anything. Don't show them a demo. Don't show them slides. Don't like focus on them. Have a one-on-one dialogue for 30 minutes. Okay. Now, again, if they're bringing in a C-suite executive, you better have your founder join that call as well.
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 43:44](https://youtu.be/19qrLchbQEc?t=2624)
  > Yeah. So this is almost always a 30 minute call. On the calendar, just I've found smaller calendar blocks they don't see on their calendar and so they don't show. And so 30 minutes and then iffy on doing a demo. So if you're super early, you probably don't have a demo to show. And

### p10: What do the guests say about the security risks of letting AI agents run things for you?
- Split: heldout  |  Author: pm_proxy
- **Gold answer:** In the beginner course the advice is to scope what the agent can access and limit tool permissions, for example read-only access to important platforms, so a compromised agent can't do much damage. The Grok Bot guest says to take the best model you have and run a /goal asking it to do security checks, and he also tests his apps with a guardrail-free 'obliterated' model.
- Key points: scope what the agent can access; read-only permissions limit damage; run security checks with best model; obliterated model attack testing
- Evidence: [AI Agents Full Course 59 Minutes (for beginners) at 8:57](https://youtu.be/eA9Zf2-qYYM?t=537)
  > I like to think of security as in just like scoping what they have access to. So by default anti-gravity Claude code and codex they're very very secure because they're built by these massive companies that have a lot on the line to protect. And I just you know if you're building out these agents
- Evidence: [I'm Obsessed With Grok Bot. Here's Why at 19:58](https://youtu.be/1cWZ7Ekff6E?t=1198)
  > What's your response to that? So the I, and the reason why I didn't share this, is I have access to an obliterated model which is basically a model where the guardrails are removed. So it's a really, really bad model. It could be a really, really bad model, but a lot of companies use

### r03: How do the guests suggest finding out whether people really want a product before you build it?
- Split: heldout  |  Author: claude
- **Gold answer:** Rob Snyder says the signal to look for is a prospect leaning in, such as an executive who says they would pay right now before there is any product. The speaker in the $1M solo business episode says to test several industries and niches with people you know and see where the market appetite is.
- Key points: leaning-in signal; pay before the product exists; test niches and see the appetite
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 25:43](https://youtu.be/19qrLchbQEc?t=1543)
  > an exec in pharma, before he had a product said, if you can do that, I will pay you right now. So, okay, that's the signal you are looking for. What you're looking for as well as they're leaning in. Wait a second, you can do what? What you're not looking for is kind of
- Evidence: [The $1M+ Solo Grok Bot Business (Full Course) at 43:55](https://youtu.be/67BmkptgTms?t=2635)
  > Just try test out a bunch of them. See what the market appetite is with people that you know and build for them. And then once you're building for them, like just genuinely sit down. Don't try and scale right away. Sit down with that one first client. Try really to solve their business, watch

### sy01: What do the guests say about working closely with early customers, even by hand, before trying to scale?
- Split: dev  |  Author: claude
- **Gold answer:** Rob Snyder says starting as a service, with humans doing the work by hand and automation built up around it, can work, though you can get stuck as a services business. The speaker in 'The $1M+ Solo Grok Bot Business' says not to scale right away: sit down with one first client, study their business and watch them.
- Key points: start by hand; one first client; do not scale too early
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 59:16](https://youtu.be/19qrLchbQEc?t=3556)
  > Yeah. And you can sell something that's like, you know, you might not have a full platform ready. You can sell something that's more service shaped early on. I've seen a bunch of startups do that where they sell, you know, okay, we're going to have an AI product manager who can do X, Y,
- Evidence: [The $1M+ Solo Grok Bot Business (Full Course) at 44:10](https://youtu.be/67BmkptgTms?t=2650)
  > Don't try and scale right away. Sit down with that one first client. Try really to solve their business, watch them, shadow them, ask them to like share their screen and go through a process of like something that they do manually, like creating an invoice or, you know, creating products into a presentation and

### sy02: What do the guests say about using content to get a product noticed?
- Split: heldout `raj`  |  Author: claude
- **Gold answer:** Sachin Puri suggests a small business build content around real success stories of founders, and says AI can now produce that content. The speaker in the $1M solo business episode says to make content about your product because people will eventually try it once they have seen you enough.
- Key points: success-story content; AI can make it; keep making content
- Evidence: [Billion-Dollar Tech CEO: How To Make AI Work Like 100 Employ at 47:18](https://youtu.be/8ol3j7o1U7o?t=2838)
  > on SEO as well but somebody who's starting as a small business build a content around that. This is what this interviewer said. This is what they were trying to figure out. Here is a person who actually started from nothing and they became so successful by figuring how to rise against all odds, never
- Evidence: [The $1M+ Solo Grok Bot Business (Full Course) at 20:48](https://youtu.be/67BmkptgTms?t=1248)
  > So yeah, if you guys aren't making content yet for your product, do it because eventually people will see you enough when you make so much content that they'll try your thing. That's how I try T3. And I actually, so my take on it is it's very good. It's very simple. And you can

### sy04: How do the guests say AI is changing marketing and creative work?
- Split: dev  |  Author: claude
- **Gold answer:** In 'AI Agents are too good at marketing now', the speaker says marketing is now just code, software and tokens, and the work of UGC creators, editors and motion designers is handled by bots. In the AI wrappers episode the guest says a top 1% marketing engineer covers SEO, GEO, social and paid ads and has an unfair advantage, while the other 98% risk becoming dinosaurs.
- Key points: marketing is code; creators replaced by bots; top 1% marketing engineer
- Evidence: [AI Agents are too good at marketing now at 5:18](https://youtu.be/uJuxenfe-NU?t=318)
  > Like all marketing is now just code. It's just software and tokens. And so when you look at, you know, an it static image for ads that you generate, when you look at... you know, a C dance video that you create where before I used to hire, have to hire like an avatar, you're
- Evidence: [Stop building AI wrappers. Start building agent harnesses. at 33:35](https://youtu.be/st61aKW8P5A?t=2015)
  > Going back to marketing engineering, in your mind, what does a top 1% marketing engineer look like? Um, well, one thing that comes to mind is they're really a marketing engineer data scientist. So they are like ultra data driven and grounded in what's performing. And this is something that's gotten easier than ever, like

### sy07: How do the guests describe charging a customer money up front?
- Split: dev  |  Author: claude
- **Gold answer:** Jen Abel says that for a 30-day value case you charge up front and credit it back against the later contract, and that price should follow the sales cycle. In the $1M solo business episode the speaker describes charging a business owner $25,000 for an implementation, collecting half up front and the rest at the end.
- Key points: charge and credit back; price follows sales cycle; half up front, half at the end
- Evidence: [How to close $100K+ enterprise deals, step by step | Jen Abe at 59:37](https://youtu.be/YS9In813jJ0?t=3577)
  > Your price should be predicated on your sales cycle, right? Like if you can get a deal done in 90 days for 100K, do that all the time, right? If it takes nine months to get a deal done, you probably should be charging 250, 300K. What are your thoughts on forward deployed engineers as
- Evidence: [The $1M+ Solo Grok Bot Business (Full Course) at 15:20](https://youtu.be/67BmkptgTms?t=920)
  > Maybe you collect half of that up front and then the other half at the end of the implementation of this. But let's go through the entire build out process, shall we? Let's do it. So first things first, I want to kind of walk through how I build in general because it's a principle

### sy13: What role does a friendly contact or champion inside the buyer's company play in closing a deal?
- Split: dev  |  Author: claude
- **Gold answer:** Rob Snyder says that in larger deals a champion with pull decides they want it and then helps with the project management of getting it done. Jen Abel says that as soon as the demo ends you text the person who has guided you, to get a raw debrief on how it went and whether someone was lost.
- Key points: champion with pull; project management; debrief after a demo
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 57:10](https://youtu.be/19qrLchbQEc?t=3430)
  > And so in bigger deals, enterprise deals, there's like the champion has pull and decides, yes, I want this. And then you have to do a set of like 17 demos. You have to genuflect in front of four committees. Like there's all of these things that you have to do for smaller deals. You
- Evidence: [How to close $100K+ enterprise deals, step by step | Jen Abe at 46:58](https://youtu.be/YS9In813jJ0?t=2818)
  > So as soon as the demo closes, you are texting the woman or the gentleman or whomever that has helped guide you to this point. How do you think that went? Can we grab, can I call you in like five minutes? I just want to, I want like a fresh debrief. They will give


## Who / when said it (10)

### n13: When does Josh Woodward bring up Roger Federer, and what idea does he take from him?
- Split: dev  |  Author: agent_reviewer
- **Gold answer:** At about 32:24 he mentions a book about Federer and the phrase 'explosive endurance': people who can go really hard but pace themselves so they can keep going over time. He links this to his idea of an unlearning rate.
- Key points: Roger Federer book; explosive endurance
- Evidence: [Why every company now needs to think and operate like a lab  at 32:24](https://youtu.be/3I6QYkccd3o?t=1944)
  > Based on maybe what they're seeing when they test their product or something. So unlearning rate is one. Another one I'm interested in, I read a book a year or so ago about Roger Federer, the amazing tennis player. And there was this phrase in there about Federer had explosive endurance. It's just this beautiful

### p11: Where in the Josh Woodward episode does he warn against getting attached to the product idea itself?
- Split: dev  |  Author: pm_proxy
- **Gold answer:** At about 16:15 he says to think about the problem you are falling in love with, not the product, because it takes three, four or five pivots before you either have something or conclude it didn't work. Falling in love with the product solution first, in his experience, leads to a bad time.
- Key points: fall in love with the problem not the product; three to five pivots
- Evidence: [Why every company now needs to think and operate like a lab  at 16:15](https://youtu.be/3I6QYkccd3o?t=975)
  > and this one's also maybe on the flip side of your question, is like, The people who get excited about things, usually we try to kind of think about what's the problem we're falling in love with, not the product. Because what I found is it takes three, four, five pivots before you either got

### p12: When does Lenny ask Rob Snyder about Linear beating Jira, and what is Rob's take?
- Split: heldout  |  Author: pm_proxy
- **Gold answer:** At about 51:28 Lenny raises Linear versus Jira, wondering if the better experience fits the pull framework. Rob says it only works if some users are actually blocked by something in Jira's experience, and warns that simply entering a category with better UX does not crush it (he says he made that mistake with HR software).
- Key points: Linear versus Jira; pull framework; users must be blocked by incumbent; better UX alone is not enough
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 51:28](https://youtu.be/19qrLchbQEc?t=3088)
  > And how do they respond when I show up? So I think about a company like Linear who competes with JIRA, I don't know if you know, do you know Linear? Yeah. So I'm just curious if it applies through this framework. So in my understanding, Linear wins over JIRA often because the experience is

### p13: When does Vinh Giang say your confidence shouldn't depend on a prop like a guitar or a deck of cards, and what should you rely on instead?
- Split: dev `raj`  |  Author: pm_proxy
- **Gold answer:** At about 35:40 Vinh says you can't take your guitar or your cards everywhere you go, but you do take your voice, your body language, your ability to tell stories and to listen, and nobody can take those away.
- Key points: cannot take guitar or cards everywhere; voice and body language; storytelling and listening
- Evidence: [Why Your Communication Makes People Ignore You & How To Fix  at 35:39](https://youtu.be/BgeNDG5jD60?t=2139)
  > So I did that exact same. So the lesson that came out of that was that I realized that, okay, you can't take your guitar everywhere you go. Okay. I can't take my cards everywhere I go. But what do you take with you everywhere you go? Your voice, your body language. Can anybody take

### r06: When does Jen Abel mention a small incentive, such as a free month, for signing by a set date?
- Split: heldout  |  Author: claude
- **Gold answer:** At about 1:14:38, in step 11 (papering prep), Jen Abel says to set a timeline for procurement and offer a small gift, such as a free month, if they sign by the date.
- Key points: step 11; procurement timeline; free month if signed by the date
- Evidence: [How to close $100K+ enterprise deals, step by step | Jen Abe at 1:14:39](https://youtu.be/YS9In813jJ0?t=4479)
  > Here's a little gift you'll get if you do it by the state, free month or whatever. Okay. Step 12, papering review. Yes. The best thing you can do is they're going to send you back red lines. No question. If the red lines are extensive, okay, go ahead and accept the things that are

### ww01: When does Rob Snyder describe getting the prospect's approval of the call agenda?
- Split: dev  |  Author: claude
- **Gold answer:** At about 43:08 in the episode.
- Key points: agenda approval
- Evidence: [An 86-minute guide to finding PMF | Rob Snyder (Author, The  at 43:08](https://youtu.be/19qrLchbQEc?t=2588)
  > Does that sound good to you? Get their thumbs up on the agenda. And then you earn the right to ask them some discovery questions about their poll by saying, great. Okay. Before we get to those items on your You know, on our agenda. Do you mind if I ask you a few questions

### ww04: Who brings up the idea of a dedicated frontier team, and at what point?
- Split: dev  |  Author: claude
- **Gold answer:** At about 43:44. The host (Lenny) brings it up, citing Dan Shipper's talk, and asks Josh how he feels about it.
- Key points: Dan Shipper; frontier team
- Evidence: [Why every company now needs to think and operate like a lab  at 43:44](https://youtu.be/3I6QYkccd3o?t=2624)
  > And Dan Shipper gave this really interesting talk about how to build where the tech is just constantly changing underneath you. And his advice is to have a frontier team that's dedicated to testing out the new stuff. And basically it's their job, trial the new stuff, report on what we need to pay attention

### ww06: At what point does Vinh Giang tell the story about being silent with a relative who has cancer?
- Split: heldout `raj`  |  Author: claude
- **Gold answer:** At about 1:40:02 in the episode.
- Key points: family members; cancer; silence
- Evidence: [Why Your Communication Makes People Ignore You & How To Fix  at 1:40:02](https://youtu.be/BgeNDG5jD60?t=6002)
  > I've currently in my life have two family members who are going through cancer and if you're going through this with someone you love, it's one of the hardest things to go through because as the person on the outside, there's nothing you can do. You know, they have to fight the battle. She has

### ww07: When does the presenter explain that an agent's memory works differently from a chat model's?
- Split: dev  |  Author: claude
- **Gold answer:** At about 18:07 in the episode.
- Key points: agent memory vs chat memory
- Evidence: [AI Agents Full Course 59 Minutes (for beginners) at 18:07](https://youtu.be/eA9Zf2-qYYM?t=1087)
  > be a bit of a shock moving from chat to agents is that these agents memory work a little bit different so if you're used to using chat models like chat gpt and Claude if you open up a fresh session in the one of these chats you don't give it any context you don't

### ww10: At what point does the guest explain why everything started to look like his company's output?
- Split: dev  |  Author: claude
- **Gold answer:** At about 14:58 in the episode.
- Key points: AI smells; Gamma look
- Evidence: [Stop building AI wrappers. Start building agent harnesses. at 14:58](https://youtu.be/st61aKW8P5A?t=898)
  > But once everybody started using it, everything started to look like gamma and people didn't want to be recognized as using AI. And so kind of our whole goal of this launch we just pulled off was we need to rapidly expand our sort of creative landscape. The truth is there's still going to be


## Unanswerable (on-topic, not in the library) (7)

### n14: What does Gita Gopinath say about central banks buying gold?
- Split: dev `raj`  |  Author: agent_reviewer
- **Gold answer:** Not covered anywhere in the 16 episodes. The right answer is that it is not found.
- Search phrases (must be absent): gold; central banks buying gold; bullion; gold reserves

### n15: What does Rob Snyder say about whether a startup should raise venture capital before looking for pull?
- Split: dev  |  Author: agent_reviewer
- **Gold answer:** Not covered. The right answer is that it is not found.
- Search phrases (must be absent): raise venture capital; fundraising; seed round; investors

### p14: How does Jen Abel say to structure commission for enterprise sales reps?
- Split: dev  |  Author: pm_proxy
- **Gold answer:** Not covered. The right answer is that it is not found.
- Search phrases (must be absent): commission; quota; compensation plan; OTE; base salary; bonus plan; how reps get paid

### p15: Does the beginner AI agents course show how to build agents with LangChain or CrewAI?
- Split: heldout  |  Author: pm_proxy
- **Gold answer:** Not covered. The right answer is that it is not found.
- Search phrases (must be absent): LangChain; lang chain; LangGraph; CrewAI; crew ai; AutoGen; LlamaIndex; agent SDK

### p16: Who does Sachin Puri see as Newfold's biggest rivals in web hosting?
- Split: dev `raj`  |  Author: pm_proxy
- **Gold answer:** Not covered. The right answer is that it is not found.
- Search phrases (must be absent): GoDaddy; go daddy; Wix; Squarespace; Hostinger; market share; rival; rivals

### un01: How does Jen Abel say to design a pricing page for enterprise plans?
- Split: dev  |  Author: claude
- **Gold answer:** Not covered anywhere in the library or the held-out episodes. The right answer is that it is not found.
- Search phrases (must be absent): pricing page; enterprise plans

### un06: How does Vinh Giang recommend booking guests for a podcast?
- Split: heldout `raj`  |  Author: claude
- **Gold answer:** Not covered. The right answer is that it is not found.
- Search phrases (must be absent): booking guests


## False premise (5)

### fp04: Why does Gita Gopinath say countries regularly default on their IMF loans?
- Split: heldout `raj`  |  Author: claude
- **Gold answer:** She says the opposite: nobody has ever defaulted to the IMF. The answer must correct the premise.
- Search phrases (must be absent): defaulted on; loans

### fp05: Why does Vinh Giang say you should avoid telling personal stories?
- Split: dev `raj`  |  Author: claude
- **Gold answer:** He says to document your stories. The answer must correct the premise.
- Search phrases (must be absent): avoid telling

### n18: Why does Rob Snyder say you should build the whole product before you start selling?
- Split: heldout  |  Author: agent_reviewer
- **Gold answer:** He does not say this; he says to test pull first by selling, even something service-shaped, before building. The answer must correct the premise.
- Search phrases (must be absent): build the whole product first; before selling; finish the product

### p17: Why does Vinh Giang tell people to memorise their talks word for word?
- Split: dev `raj`  |  Author: pm_proxy
- **Gold answer:** He never says this. What he recommends instead is to record yourself, have the video transcribed, and put the transcript into an AI to find your most common mistakes. The answer must correct the premise.
- Search phrases (must be absent): memorise; memorize; memorized; word for word; by heart; rote

### p18: Why does Rob Snyder say you should hire a head of sales before you've found any pull?
- Split: dev  |  Author: pm_proxy
- **Gold answer:** He never says this. His framework is about spotting pull: whether a buyer has an urgent project that must be done now (a 'hair on fire' problem), found by talking to prospects directly. Hiring comes up only as an example of a project a customer might be trying to do. The answer must correct the premise.
- Search phrases (must be absent): head of sales; hire a head of sales; first sales hire; hire a sales leader; chief revenue officer


## Indexed but not in the evaluation library (5)

### nl01: What did the nutrition expert say about salt and blood pressure?
- Split: dev `raj`  |  Author: claude
- **Gold answer:** Only in 'Diet Expert' (Raj Shamani), which is not in the evaluation library. The right answer is that it is not found in the library.
- Evidence: [Diet Expert: Weight Loss, Calories, Digestion, Sugar & Belly at 17:42](https://youtu.be/xi-zHJL5bnI?t=1062)
  > sugar. Okay, think about it. Someone gets a stroke. Someone gets a heart attack. Or someone is just collapsed out of we don't know what. Rushed him in an ambulance. Without talking to any doctors, without knowing medical history, what do you add? Saline. Saline. What is that? Saline. What is saline? Glucose. Saline. What

### nl03: Why did the Meta team keep the Jolly avatar instead of a corporate logo?
- Split: dev  |  Author: claude
- **Gold answer:** Only in 'Meta's Muse', which is not in the library. The right answer is that it is not found.
- Evidence: [Meta’s Muse: How we launched the most successful consumer pr at 26:19](https://youtu.be/WY0cdD4gNoQ?t=1579)
  > And I would say that the reason there were so many reasons, but actually Mark was one of the reasons where he was like, no, he really loved the avatar. But I think mostly it's like when you're talking to something that feels so personal, the last thing you want to talk to is a

### nl04: What was the story behind the Fitzpatrick scale and the Monk skin tone work?
- Split: heldout  |  Author: claude
- **Gold answer:** Only in 'Why PMs are suddenly valuable again', which is not in the library. The right answer is that it is not found.
- Evidence: [Why PMs are suddenly valuable again | Tulsee Doshi (Head of  at 26:41](https://youtu.be/qGf2Yvan4Wg?t=1601)
  > So one is you worked on something called the Fitzpatrick scale and the monk skin tone. And this was a big shift in how people in how models worked around and evals were a core part of this. Share this story. What this work was. Yeah. So I like like you noted earlier, I spent

### p19: What's the 60-20-20 rule Tulsee Doshi talks about for building AI products?
- Split: heldout  |  Author: pm_proxy
- **Gold answer:** Only in the Tulsee Doshi episode ('Why PMs are suddenly valuable again'), which is not in the library. The right answer is that it is not found.
- Evidence: [Why PMs are suddenly valuable again | Tulsee Doshi (Head of  at 33:26](https://youtu.be/qGf2Yvan4Wg?t=2006)
  > and how far your product should assume AI is going to be. You call that a 60-20-20 rule. Explain that. I think the numbers are probably fungible here, but I think the thesis is the same, which is I think as you're building today and as you're a product developer building using these models, I

### p20: How did the Anthropic researcher explain the Golden Gate Claude experiment?
- Split: dev  |  Author: pm_proxy
- **Gold answer:** Only in 'Inside the black box of AI', which is not in the library. The right answer is that it is not found.
- Evidence: [Inside the black box of AI: How AI models actually think | E at 38:22](https://youtu.be/JHo-aiePjoM?t=2302)
  > Among those lines, there was famously the Golden Gate Claude, which was just obsessed with the Golden Gate and every answer and kind of find some way to reference the Golden Gate Bridge. Yes, yes. Well, that one was an interp experiment, right? So like the cool part of that one is we just found

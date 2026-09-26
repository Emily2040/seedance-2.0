# Event Density

Use this reference to decide how much story belongs in one generation.

## Density Rule

One generation should normally carry one visible beat with a changed endpoint. Long backstory, multiple locations, multiple major actions, dense dialogue, and future resolution belong in the sequence plan, not the current prompt.

## Beat Buckets

`already_happened`: do not replay.

`this_clip_only`: the current prompt may perform this.

`reserved_for_later`: do not show yet.

`do_not_show_yet`: excluded even if it explains motivation.

## Scope Firewall

Story context can inform motivation, performance, atmosphere, and pacing. It must not cause the current clip to perform future events, reveal future information, solve later problems, or skip physical handoff states.

## Official Density Warning

ByteDance's own troubleshooting notes for Seedance 2.0 state the rule in both directions (recorded 2026-09-26 from the `bytedance/agentkit-samples` repository; recheck before quoting as current):

> 视频时长过长但提示词剧情内容较少，会导致模型自行发挥。视频时长过短但提示词内容包含多个分镜，会导致视频内容/人物台词乱说。

Too much duration for too little content and the model improvises; too little duration for several shots and the content and the lines garble. The remedy in the same file is to split: 把原来的四个镜头拆成两个视频，给够人物说英文台词的时间, four shots become two videos so the English line has time to be spoken.

This repository's planning number for that warning is the load score in [multishot-grammar](multishot-grammar.md): seconds per load point S = duration ÷ (beats + load). S of 3.0 or more is Safe, 2.0 to 3.0 is Stretch, under 2.0 is Ambitious and the split is the recommended spend. The thresholds are authored heuristics awaiting rendered calibration, not official limits. Shape comes first: a single continuous action in one scene is one paragraph and needs no score.

## Splitting Triggers

Split when a request asks for several completed actions, a journey with multiple locations, several turns of dialogue, complex physical contact, product proof plus hero packshot, a storyboard whose load score falls under 2.0, or a story longer than the verified active-surface duration.

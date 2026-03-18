# UAT Post-Test Survey

## Section 1: Comparison to Current Manual Review Process

1. Compared with your usual process for reviewing data after the first pass of the extraction pipeline, how did using the dashboard affect the time required to complete the inspection task?
- Much longer
- Somewhat longer
- About the same
- **Somewhat shorter**
- **Much shorter**

2. Roughly how much faster or slower did it feel?
- More than 50% slower
- 25–50% slower
- 10–25% slower
- About the same
- 10–25% faster
- 25–50% faster
- **More than 50% faster** -for metrics precomputed and summary plot view
- Not sure

3. If you were doing this work as part of your normal workflow, which would you prefer to use for post-extraction review?
- **Dashboard** -Summary plot is the key deciding factor
- Manual process
- No preference
- Not sure

4. Please explain your answer to the previous question.

-Summary plot is the key deciding factor
On the fly pose a bunch of hypothesis in your head: one of the reasons the extraction failed is because it captured two side by side footsteps and comparing allows a more immediate comparison of those misaligned trials. 

most useful immediate future goal: identify misaligned trial or outlier, tweak that trial then re-run processing to see if you can observe a better outcome. 

5. Which part of the dashboard contributed most to efficient review?
- **Swipe event filtering**
- **Swipe event summary view**
- Footstep view
- Temporal exploration tools
- P100 / heatmap visualization
- Pressure-over-time graph
- Editing tools
- Change log
- Other: **2D plot**

6. Which part of the dashboard most limited efficiency?
- Swipe event filtering
- Swipe event summary view
- Footstep view
- Temporal exploration tools
- P100 / heatmap visualization
- Pressure-over-time graph
- Editing tools
- **Change log** wasn't implemented fully
- Other: 

## Section 2: Alignment with Functional Requirements

7. Did the separation between the swipe-event view and the footstep-focused view make sense for your workflow?
- **Yes** --selection on 2D scatterplot ripples into footstep view below. 
- No
- Partially

8. Did the swipe event summary view provide enough information to inspect extracted footsteps within the full swipe event?
- **Yes***
- No
- **Partially** --culmulative and single swipe event footsteps do not match full event image.

9. Which parts of the swipe event summary view were most useful during review?
- **Temporal/frame view**
- P100 visualization
- Footstep highlighting
- Pressure-over-time graph
- Other: **progressing through trial step by step**

10. Did the footstep-focused view support the kind of inspection and comparison you would want during normal post-extraction review?
- **Yes** -- grf and cop data could be useful for this view in the future
- No
- Partially

11. Did the filtering and selection tools behave in a way that matched your expectations?
- **Yes** - very intuitive
- No
- Partially

12. How easy was it to use the filtering and graph-selection tools?
- Very difficult
- Difficult
- Neutral
- Easy
- **Very easy**

13. How clear were the following workflows?
- Editing an existing footstep
- Creating a new footstep
- Deleting a footstep

Response scale for each:
- Very unclear
- Unclear
- Neutral
- Clear
- **Very clear** * * * 

time selection is the least clear 

14. Did the change log provide enough traceability for the edits you made?
- **Yes**
- No
- **Partially*** -- accompanying image/thumbnail with each input of the changelog would help speed up processing

## Section 3: Confidence, Fit, and Improvements

15. At any point, were you unsure what the system would do to the data when making a change?
- Yes
- **No**

16. If yes, please describe that moment. **n/a**

17. Did the dashboard support the parts of your post-extraction inspection workflow that matter most?
- **Yes** - Prioritization of problematic trials and 2D scatterplot image. Outlier indicators
- No
- Partially

18. What part of your normal post-extraction workflow is still missing, unclear, or uncomfortable in this dashboard?
-re run extraction pipeline with a different set of parameters

19. What single change would most improve the dashboard for post-extraction manual inspection?
- **filtering**
easier ability to select complex filters. selecting multple participants is one-click-per. 
Increased customizability in the filtering 
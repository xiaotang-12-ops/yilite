<!-- memory-id: mem_1769822205425_zi45k66 -->
# 2026-01-31
TITLE: Multi-agent system performance optimization and token consumption analysis
TAGS: #performance #token_optimization #agent_system #user_project
CONTENT:
- User has a multi-agent system (Agent1-6) processing technical drawings with severe performance issues (1 hour runtime)
- System processes 58 assembly steps through Agent4, Agent5 (welding expert), and Agent6 (safety expert) sequentially
- Agent5 consumes ~30,000 tokens (3 images + 58 steps JSON), Agent6 consumes ~40,000 tokens (58 steps with welding info)
- Total token consumption: ~80,000 tokens per run, potentially 150,000-200,000 with retries
- Performance bottlenecks: large data volume (58 steps vs previous 20-30), serial processing, full data transmission instead of incremental, repeated image encoding
- User is highly sensitive to performance and cost issues
- User prefers sequential thinking for deep analysis and needs detailed input/output file specifications to track token consumption
- Optimization directions identified: batch processing (10-15 steps per batch), reduce image transmission, optimize data structure (remove unnecessary node_name fields), parallel processing
- User has interrupt mechanism that was tested before BOM matching, interrupted twice, may have caused duplicate processing
<!-- memory-id: mem_1770003209332_r9tlwnm -->
# 2026-02-02
TITLE: BOM extraction strategy shift from AI Vision to PDF text layer parsing
TAGS: #bom_extraction #pdf_parsing #text_layer_priority #vision_fallback
CONTENT:
- User proposed replacing AI Vision-based BOM extraction with direct PDF text layer parsing to reduce cost and improve accuracy
- System already has pdf_text_bom_extractor.py that can extract 7 BOM fields: seq/code/product_code/name/quantity/unit_weight/total_weight
- Current issue: text layer extraction only got 37/58 items, marked as unreliable, fell back to Vision which introduced errors (01.03.5275 misread as 01.03.5276)
- Text layer plausibility criteria: seq starts from 1, continuity ≥70%, minimum 8 records
- Agreed strategy: text layer priority with Vision as fallback - text layer corrections should override Vision errors even when incomplete
- Need to implement correction log (step2_bom_correction_log.json) to track when text layer overrides Vision values
- Need duplicate code detection to alert user of potential issues
- Long-term goal: optimize text layer extraction to handle complex PDF formats (multi-page, multi-column, special layouts) and eventually replace Vision completely
- User wants phased implementation: Phase 1 (immediate) - text layer priority correction + duplicate detection; Phase 2 (long-term) - enhance text layer extraction completeness
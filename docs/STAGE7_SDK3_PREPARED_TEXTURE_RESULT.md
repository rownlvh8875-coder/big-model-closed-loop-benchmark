# SDK3 prepared terrain textures and resident mip1 result

Checked 2026-11-17T19:55:20.725795+09:00. Draft PR142 is stacked on unchanged PR141 (base bf71fb9a794506b1fc64f996f4ff062cbb1b98a4). **This is a diagnostic result; official matrix remains3/4 PASS, overallFAIL, Stage7=false.**

## Result and limits

**New observation:** CPU baselevel corners are all0, while the already-resident mip1 center is `[0,0,0.07500000298023224,0]`, bilinear0.01687556688432301. All five mip1 CPU candidate values0.016021417878921834–0.017166276122241208 enter the shader's `.01 < value < .11` yellow predicate. The captured Road7 pixel remains gray[167,163,158]. This separates a CPU mip effect from proof of the rendered result.

Attribute base22528² exceeds cached max16384. CPU minimum cap bias1 gives11264²; reported graphics bytes126877696 equal11264²×1B and also5632²×4B. Byte count alone cannot choose between size and component format. The pinned desktop GL source maps `F_red` with `T_float` to `GL_R8_SNORM` (GLsource10453, Texture::is_unsigned2604), which is compatible with the one-byte mip1 model, distinct from CPUfloat32. Actual hardware internal format/bias remains unmeasured.

Prepared metadata complete: **True**; existing attribute mip1 collection complete: **True**. Observed 1 cached GSG context(s),3 owner textures,20 mip1 float32 texels/80B; unchanged base observation 200B, combined 280B. New prepared observer 0.0008803790000229128s,RSS highwater delta 0KiB. Metadata/sample observation performs no preparation, generation, GPU query/readback, setter or extra render/task.

A positive cached dimension cap gives a **CPU minimum halving bias**, and reported graphics bytes may agree with a level's uncompressed size. This supports examining the original upload's mip selection; it does not measure hardware texture dimensions or prove actual upload bias. `is_prepared` includes queued objects; recent-frame activity cannot identify the target pixel; cached bytes may persist when nonresident. RAM mip values at projected CPU GeomNode candidates are not actual procedural terrain intersections or GPU sampler values. Pixel-owner, hardware-dimensions, GPU-execution, unique-cause and repair flags remain false.

## Cached GSG limits

|Context|GSG pointer|PGO pointer|Cached maximum2D dimension|NPOT support|Effective texture stages|
|---|---|---|---|---|---|
|0|94411837636944|94411837641824|16384|True|8|

## Per-owner texture cache

|Role|Context|Queued or prepared|Reported graphics bytes|Active recent frame|Reported resident|Image modified/unprepared|CPU minimum bias|
|---|---|---|---|---|---|---|---|
|attribute|0|True|126877696|True|True|False|1|
|heightfield|0|True|8388608|True|True|False|0|
|yellow|0|True|4194304|True|True|False|0|

Expected mip sizes are recomputed from base dimensions; first four RAM-level metadata only. Distinct GSGs may share PGO, so the receiver deduplicates GSG pointers and retains PGO identity. Full cache and mip metadata: [prepared-analysis.json](evidence/sdk3-prepared-texture-01/actual/prepared-analysis.json).

## Already-resident attribute mip1 windows

|Candidate ray|Status|Four raw float32 values|CPU mip1 bilinear value|CPU yellow predicate|
|---|---|---|---|---|
|center|CAPTURED|[0.0, 0.0, 0.07500000298023224, 0.0]|0.01687556688432301|True|
|top_left|CAPTURED|[0.0, 0.0, 0.07500000298023224, 0.0]|0.017166276122241208|True|
|top_right|CAPTURED|[0.0, 0.0, 0.15000000596046448, 0.07500000298023224]|0.016021417878921834|True|
|bottom_right|CAPTURED|[0.0, 0.0, 0.15000000596046448, 0.07500000298023224]|0.016021417878921834|True|
|bottom_left|CAPTURED|[0.0, 0.0, 0.07500000298023224, 0.0]|0.017166276122241208|True|

Absent/unsupported mip1 remains explicit unavailable and incomplete; no mipmap is created. Every recorded corner's byte offset,UV,expected extent,raw SHA,owner pointer and sample index was revalidated. CPU bilinear arithmetic uses the existing default wrap policy and is not a rendering measurement.

## Actual capture and equivalence

Native completed: True; source images authenticated: 14; source equivalence: **False**; renderer diagnostic pass: **False**; status `INCONCLUSIVE_PREPARED_TEXTURE_RECORDED`. Road7 full source SHA `3d7ced2bf6e8c448d5f99695c03221599150c1c93f44e2abb28105041c67054f`. All14actual images were compared to both frozen historical prefixes (28historical source images), with exact image/manifest/report binding.

```json
[
  {
    "reference_run": 0,
    "camera": "road",
    "step": 2,
    "metrics": {
      "bit_exact": false,
      "changed_pixel_count": 1,
      "total_pixels": 582256,
      "changed_channel_values": 3,
      "changed_channels_rgb": [
        1,
        1,
        1
      ],
      "maximum_absolute_channel_delta": 89,
      "bounding_box_xyxy_inclusive": [
        401,
        393,
        401,
        393
      ],
      "first_12_changed_xy": [
        [
          401,
          393
        ]
      ],
      "changed_pixel_counts_grid_4x4_top_left_to_bottom_right": [
        [
          0,
          0,
          0,
          0
        ],
        [
          0,
          0,
          0,
          0
        ],
        [
          0,
          1,
          0,
          0
        ],
        [
          0,
          0,
          0,
          0
        ]
      ],
      "changed_mask_is_not_a_shadow_or_lane_semantic_segmentation": true
    },
    "changed_rgb": [
      {
        "xy": [
          401,
          393
        ],
        "historical": [
          135,
          144,
          82
        ],
        "actual": [
          179,
          176,
          171
        ]
      }
    ]
  },
  {
    "reference_run": 1,
    "camera": "road",
    "step": 2,
    "metrics": {
      "bit_exact": false,
      "changed_pixel_count": 1,
      "total_pixels": 582256,
      "changed_channel_values": 3,
      "changed_channels_rgb": [
        1,
        1,
        1
      ],
      "maximum_absolute_channel_delta": 89,
      "bounding_box_xyxy_inclusive": [
        401,
        393,
        401,
        393
      ],
      "first_12_changed_xy": [
        [
          401,
          393
        ]
      ],
      "changed_pixel_counts_grid_4x4_top_left_to_bottom_right": [
        [
          0,
          0,
          0,
          0
        ],
        [
          0,
          0,
          0,
          0
        ],
        [
          0,
          1,
          0,
          0
        ],
        [
          0,
          0,
          0,
          0
        ]
      ],
      "changed_mask_is_not_a_shadow_or_lane_semantic_segmentation": true
    },
    "changed_rgb": [
      {
        "xy": [
          401,
          393
        ],
        "historical": [
          135,
          144,
          82
        ],
        "actual": [
          179,
          176,
          171
        ]
      }
    ]
  },
  {
    "reference_run": 1,
    "camera": "road",
    "step": 7,
    "metrics": {
      "bit_exact": false,
      "changed_pixel_count": 1,
      "total_pixels": 582256,
      "changed_channel_values": 3,
      "changed_channels_rgb": [
        1,
        1,
        1
      ],
      "maximum_absolute_channel_delta": 158,
      "bounding_box_xyxy_inclusive": [
        596,
        494,
        596,
        494
      ],
      "first_12_changed_xy": [
        [
          596,
          494
        ]
      ],
      "changed_pixel_counts_grid_4x4_top_left_to_bottom_right": [
        [
          0,
          0,
          0,
          0
        ],
        [
          0,
          0,
          0,
          0
        ],
        [
          0,
          0,
          0,
          0
        ],
        [
          0,
          0,
          1,
          0
        ]
      ],
      "changed_mask_is_not_a_shadow_or_lane_semantic_segmentation": true
    },
    "changed_rgb": [
      {
        "xy": [
          596,
          494
        ],
        "historical": [
          199,
          187,
          0
        ],
        "actual": [
          167,
          163,
          158
        ]
      }
    ]
  }
]
```

The original Road7 image had already been read when the added prepared observer ran inside that boundary. Differences across fresh runs demonstrate that the frozen divergence remains; this does not establish causal attribution or exclude timing effects on later operations. Full comparison: [source-prefix-pixel-comparison.json](evidence/sdk3-prepared-texture-01/actual/source-prefix-pixel-comparison.json).

## Execution and provenance

- Source `b759849d911190a2d3376b0f90daa330d8192c1c`, activation `051b0f33ca2684d072363b42a4cba84a517cb2e3`; request-only branch diagnostic/sdk3-prepared-texture-20261117-01,attempt1. [Actual run 44067526874](https://github.com/rownlvh8875-coder/big-model-closed-loop-benchmark/actions/runs/44067526874), workflow 421213685; one renderer,zero official model processes/ONNX inferences.
- Artifact 14320743853,16516115B,`sha256:f5bbd810ad6369c64cece2e5c828b33b4eb43356b2069ca7136338c235144aad`. ZIP and all bundle files retained in `output/stage7-sdk3-prepared-texture-01/actual/`; [retained-index.json](evidence/sdk3-prepared-texture-01/actual/retained-index.json) maps Git receipts and raw images/geometry.
- Same immutable image tarSHA4984470cd7d732f9f2d1c12710c9433b563b3817ba6d1d419749a9a2b1b46698,SDK SHA27cd80fb1c06feaa7da8b5658cce918d1e3ab71c304a0c0ce42e30688ac008f3,core8b0372f1df91a930f18b2551f7fde5d5687e21bc79dee9ecd0dd2018cba72490,BaseCamera23d90c3d12894f855ae64d4607c03f3bf34e31e28dd7f5ce82bd0ddc7b37faf5. Frozen RGB origin43854755697/artifact14220249832 unchanged.
- Existing2CPU/10GiB/networknone/privateIPC/readonlyroot/uid65534/tmpfs512MiB,600s child/630s container/20min job bounds unchanged. Lifecycle and journal/stack receipts: [boundary-analysis.json](evidence/sdk3-prepared-texture-01/actual/boundary-analysis.json).
- [Pinned API reference](evidence/sdk3-prepared-texture-01/reference-index.json): Panda1.10.13 commit470e352ab87ceae6e30429720e4690c8371f5a55,15files1284742B,eachSHA/size verified. It documents cached getters and original GL upload's bias loop; it is not runtime binary source attestation. Inert.data files are never imported/executed.

## Validation and closeout

New15tests include actual readonly507510784B sparse-map literal bytes, cap inference/queue semantics, real native snapshot over CPU doubles, final identity/extent/UV/offset/hash/count/flag mutation rejection, absent/partial/RSS32768–32769KiB and cold-I-S bootstrap. Focused146testsPASS; actionlintPASS. Sole fresh reviewer gpt-6-astra/high independently110testsPASS; Critical0/Important0/Minor0; no fix pass/rereview.

Exactsource push44066782185 andPR44066792018 each2114tests/7skips; four canonical jobsPASS/attempt1/artifacts0, including generated small ONNX integration test. All source CI receipts in [source-ci-reviewed](evidence/sdk3-prepared-texture-01/source-ci-reviewed/verification.json). After this evidence commit, exactfinalHEAD push/PR CI and remote Draft/body/parent/main/original checks are recorded in `output/stage7-sdk3-prepared-texture-01/final-closeout/verification.json` to avoid a self-referential commit SHA. Original checkout and six file hashes/modes preserved; source code remains identical to executedsource. Own ledger is archived, only own scratch removed at completion. No main merge/environment or registry publication.

Next unresolved question is how actual procedural terrain draw coordinates, the texture's internal format and sampler precision relate to the divergent pixel. A bounded CPU quantization/coordinate analysis can refine this hypothesis; actual draw/GPU state remains unobserved. This run does not prove a repair.

# LifeWatch 95 类三大类映射

日期：2026-07-29

## 目的

将 LifeWatch FlowCam 训练集的 95 个细分类映射为本项目的三大类：

1. 藻类
2. 非藻类生物
3. 非生物杂质

本映射用于后续建立粗粒度三分类数据集、统计样本量和转换训练标签；不修改原始 `classes.txt` 的类别 ID 或顺序。

## 数据来源与判定原则

- 原始类别文件：`code/algae_guardian/data/Flowcam_images_training_split_metadata/Flowcam_images_training_split_metadata/dataset_files_equal/classes.txt`
- 数据集：LifeWatch FlowCam v2，95 类、337,514 张图像。
- 原始元数据将标签划分为 phytoplankton、protozoa 和 zooplankton。细节见 [LifeWatch taxonomy metadata](https://lifewatch.be/sites/lifewatch.be/files/public/metadata_taxonomy.pdf)。
- 本文中的“非生物杂质”是模型任务定义：包括非目标颗粒、成像伪影和悬浮污染物。它不严格等同于“没有生物来源”；例如碎屑、粪粒和花粉在训练中仍按杂质处理。
- 原始元数据定义为 zooplankton 的动物残片或骨针，仍归入“非藻类生物”，以保留其生物学来源和外观特征。

## 汇总

| 三大类     | 原始细分类数量 | 类别 ID                                                                                                           |
| ---------- | -------------: | ----------------------------------------------------------------------------------------------------------------- |
| 藻类       |             68 | 0, 1, 2, 5-15, 17-23, 26, 27, 31-33, 35, 40-49, 52-57, 59, 61, 62, 66-69, 71, 72, 74-76, 78, 79, 81-84, 87, 89-93 |
| 非藻类生物 |             20 | 3, 24, 25, 28, 29, 34, 37, 39, 50, 51, 60, 64, 65, 73, 77, 80, 85, 86, 88, 94                                     |
| 非生物杂质 |              7 | 4, 16, 30, 36, 38, 63, 70                                                                                         |

说明：类别 ID 从 0 开始，对应下表的“序号 - 1”。

## 完整映射表

| 序号 | 原始标签                                                    | 建议中文展示名             | 三大类     | 备注                       |
| ---: | ----------------------------------------------------------- | -------------------------- | ---------- | -------------------------- |
|    1 | Actinoptychus                                               | 放射纹藻属                 | 藻类       | 硅藻                       |
|    2 | Actinoptychus senarius                                      | 六辐放射纹藻               | 藻类       | 硅藻                       |
|    3 | Actinoptychus splendens                                     | 华丽放射纹藻               | 藻类       | 硅藻                       |
|    4 | Appendicularia                                              | 尾海鞘类                   | 非藻类生物 | 浮游动物                   |
|    5 | Artefact                                                    | 成像伪影/杂质              | 非生物杂质 |                            |
|    6 | Asterionella                                                | 星杆藻属                   | 藻类       | 硅藻                       |
|    7 | Aulacodiscus argus                                          | 阿古斯管盘藻               | 藻类       | 硅藻                       |
|    8 | Bacillaria paxillifer                                       | Paxillifer 杆状藻          | 藻类       | 硅藻                       |
|    9 | Bacillariophyceae                                           | 硅藻纲                     | 藻类       | 未细分硅藻                 |
|   10 | Bacillariophyceae_type1_colony                              | 硅藻群体 I 型              | 藻类       |                            |
|   11 | Bacteriastrum                                               | 细柱藻属                   | 藻类       | 硅藻                       |
|   12 | Bellerochea                                                 | 贝勒罗藻属                 | 藻类       | 硅藻                       |
|   13 | Bellerochea horologicalis                                   | 钟形贝勒罗藻               | 藻类       | 硅藻                       |
|   14 | Biddulphia alternans                                        | 交替双壁藻                 | 藻类       | 硅藻                       |
|   15 | Biddulphianae                                               | 双壁藻类                   | 藻类       | 硅藻                       |
|   16 | Brockmanniella brockmannii                                  | 布罗克曼藻                 | 藻类       | 硅藻                       |
|   17 | Bubbles                                                     | 气泡                       | 非生物杂质 |                            |
|   18 | Cerataulus granulata                                        | 颗粒角状藻                 | 藻类       | 硅藻                       |
|   19 | Ceratium horridum/C. longipes                               | 恐角藻/长角藻              | 藻类       | 甲藻                       |
|   20 | Chaetoceros                                                 | 角毛藻属                   | 藻类       | 硅藻                       |
|   21 | Chaetoceros affinis                                         | 近缘角毛藻                 | 藻类       | 硅藻                       |
|   22 | Chaetoceros curvisetus/C. pseudocurvisetus                  | 曲角毛藻/拟曲角毛藻        | 藻类       | 硅藻                       |
|   23 | Chaetoceros danicus                                         | 丹麦角毛藻                 | 藻类       | 硅藻                       |
|   24 | Chaetoceros socialis                                        | 社会角毛藻                 | 藻类       | 硅藻                       |
|   25 | Cnidaria                                                    | 刺胞动物                   | 非藻类生物 | 浮游动物                   |
|   26 | Copepoda adult                                              | 成年桡足类                 | 非藻类生物 | 浮游动物                   |
|   27 | Coscinodiscus concinnus                                     | 匀称圆筛藻                 | 藻类       | 硅藻                       |
|   28 | Coscinodiscus granii                                        | 格拉恩圆筛藻               | 藻类       | 硅藻                       |
|   29 | Crustacea                                                   | 甲壳类                     | 非藻类生物 | 浮游动物                   |
|   30 | Crustaceae:part                                             | 甲壳类残片                 | 非藻类生物 | 保留动物来源               |
|   31 | Detritus                                                    | 碎屑                       | 非生物杂质 | 按非目标杂质处理           |
|   32 | Dinoflagellate cyst                                         | 甲藻孢囊                   | 藻类       | 甲藻                       |
|   33 | Diploneis                                                   | 双眉藻属                   | 藻类       | 硅藻                       |
|   34 | Ditylum brightwellii                                        | Brightwell 双锥藻          | 藻类       | 硅藻                       |
|   35 | Egg/Cyst                                                    | 卵/囊体                    | 非藻类生物 | 默认归类；训练前应人工复核 |
|   36 | Eucampia                                                    | 优卡藻属                   | 藻类       | 硅藻                       |
|   37 | Faecal pellet                                               | 粪粒                       | 非生物杂质 | 按非目标杂质处理           |
|   38 | Favella                                                     | 法韦拉壳虫属               | 非藻类生物 | 纤毛虫                     |
|   39 | Fibers                                                      | 纤维杂质                   | 非生物杂质 |                            |
|   40 | Foraminifera                                                | 有孔虫                     | 非藻类生物 | 原生生物                   |
|   41 | Guinardia delicatula                                        | 纤细几内亚藻               | 藻类       | 硅藻                       |
|   42 | Guinardia flaccida                                          | 松弛几内亚藻               | 藻类       | 硅藻                       |
|   43 | Guinardia striata/Dactyliosolen phuketensis                 | 条纹几内亚藻/普吉圆筒藻    | 藻类       | 硅藻                       |
|   44 | Helicotheca tamesis                                         | 泰晤士螺纹藻               | 藻类       | 硅藻                       |
|   45 | Hobaniella longicruris                                      | 长足霍巴尼藻               | 藻类       | 硅藻                       |
|   46 | Lauderia/Melosira/Detonula                                  | 劳德里藻/直链藻/德托努拉藻 | 藻类       | 硅藻                       |
|   47 | Leptocylindraceae                                           | 细圆筒藻科                 | 藻类       | 硅藻                       |
|   48 | Lithodesmium undulatum                                      | 波状石盾藻                 | 藻类       | 硅藻                       |
|   49 | Melosira                                                    | 直链藻属                   | 藻类       | 硅藻                       |
|   50 | Meuniera membranacea                                        | 膜状梅尼耶藻               | 藻类       | 硅藻                       |
|   51 | Mollusca                                                    | 软体动物                   | 非藻类生物 | 浮游动物                   |
|   52 | Nauplii                                                     | 无节幼体                   | 非藻类生物 | 甲壳类幼体                 |
|   53 | Neocalyptrella robusta                                      | 强壮新卡利普特雷拉藻       | 藻类       | 硅藻                       |
|   54 | Noctiluca scintillans                                       | 夜光虫                     | 藻类       | 数据集标注为甲藻           |
|   55 | Noctilucales                                                | 夜光虫目                   | 藻类       | 数据集标注为甲藻           |
|   56 | Odontella aurita/Ralfsiella minima                          | 耳状齿状藻/小拉夫藻        | 藻类       | 硅藻                       |
|   57 | Odontella rhombus f. trigona                                | 三角变型菱形齿状藻         | 藻类       | 硅藻                       |
|   58 | Paralia                                                     | 平板藻属                   | 藻类       | 硅藻                       |
|   59 | Pennate Diatom                                              | 羽纹硅藻                   | 藻类       |                            |
|   60 | Pennate Diatom colony                                       | 羽纹硅藻群体               | 藻类       |                            |
|   61 | Peritrichia                                                 | 周毛类纤毛虫               | 非藻类生物 | 原生生物                   |
|   62 | Phytoplankton Colony                                        | 浮游植物群体               | 藻类       |                            |
|   63 | Plagiogrammopsis/Bellerochea malleus                        | 拟斜纹藻/锤形贝勒罗藻      | 藻类       | 硅藻                       |
|   64 | Pollen                                                      | 花粉                       | 非生物杂质 | 按非目标杂质处理           |
|   65 | Polychaeta                                                  | 多毛类                     | 非藻类生物 | 浮游动物                   |
|   66 | Porifera spicule                                            | 海绵骨针                   | 非藻类生物 | 保留动物来源               |
|   67 | Proboscia alata                                             | 翼鼻藻                     | 藻类       | 硅藻                       |
|   68 | Proboscia indica                                            | 印度鼻藻                   | 藻类       | 硅藻                       |
|   69 | Protoperidinium pentagonum                                  | 五角前沟藻                 | 藻类       | 甲藻                       |
|   70 | Pseudo-nitzschia                                            | 伪菱形藻属                 | 藻类       | 硅藻                       |
|   71 | Remnant                                                     | 残片/残余物                | 非生物杂质 | 按非目标杂质处理           |
|   72 | Rhizosolenia                                                | 根管藻属                   | 藻类       | 硅藻                       |
|   73 | Rhizosolenia setigera (f. pungens)/R. hebetata f. semispina | 刚毛根管藻/钝根管藻        | 藻类       | 硅藻                       |
|   74 | Rotifera                                                    | 轮虫                       | 非藻类生物 | 浮游动物                   |
|   75 | Skeletonema                                                 | 骨条藻属                   | 藻类       | 硅藻                       |
|   76 | Stellarima stellaris/Podosira/Hyalodiscus                   | 星轮藻/柄圆盘藻/透明圆盘藻 | 藻类       | 硅藻                       |
|   77 | Stephanopyxis                                               | 冠盖藻属                   | 藻类       | 硅藻                       |
|   78 | Suctoria                                                    | 吸管虫                     | 非藻类生物 | 原生生物                   |
|   79 | Synedra/Thalassionema                                       | 针杆藻/海线藻              | 藻类       | 硅藻                       |
|   80 | Thalassiosira/Porosira                                      | 海链藻/孔圆筛藻            | 藻类       | 硅藻                       |
|   81 | Tintinnopsis                                                | 小铃虫属                   | 非藻类生物 | 纤毛虫                     |
|   82 | Triceratium favus                                           | 蜂窝三角藻                 | 藻类       | 硅藻                       |
|   83 | Trieres mobiliensis/T. regia                                | 莫比利斯三棱藻/王三棱藻    | 藻类       | 硅藻                       |
|   84 | Trieres sinensis                                            | 中国三棱藻                 | 藻类       | 硅藻                       |
|   85 | Tripos fusus                                                | 纺锤角藻                   | 藻类       | 甲藻                       |
|   86 | Veliger larvae D-shaped                                     | D 形面盘幼体               | 非藻类生物 | 双壳类幼体                 |
|   87 | Zooplankton                                                 | 浮游动物                   | 非藻类生物 | 未细分                     |
|   88 | Zygoceros                                                   | 合角毛藻属                 | 藻类       | 硅藻                       |
|   89 | Tintinnina                                                  | 铃壳虫类                   | 非藻类生物 | 纤毛虫                     |
|   90 | Dactyliosolen/Cerataulina/Guinardia                         | 圆筒藻/角状藻/几内亚藻     | 藻类       | 硅藻                       |
|   91 | Protoperidinium                                             | 前沟藻属                   | 藻类       | 甲藻                       |
|   92 | Tripos                                                      | 角藻属                     | 藻类       | 甲藻                       |
|   93 | Dinoflagellata                                              | 甲藻类                     | 藻类       |                            |
|   94 | Centric Diatom                                              | 中心硅藻                   | 藻类       |                            |
|   95 | Ciliophora                                                  | 纤毛虫门                   | 非藻类生物 | 原生生物                   |

## 训练前注意事项

1. `Egg/Cyst`（ID 34）不能直接视为高置信度的非藻类生物。原始数据说明平滑的甲藻孢囊也被归到该类；构建首版三分类训练集时，建议先从训练集抽样复核，或暂时从训练、验证和测试中同时剔除。
2. `Detritus`、`Faecal pellet`、`Pollen` 和 `Remnant` 具有生物来源的可能，但它们不是本项目需要识别的完整目标生物，统一作为“非生物杂质/非目标杂质”。
3. `Crustaceae:part` 和 `Porifera spicule` 是动物残片。本文归入“非藻类生物”，方便模型学习其生物组织或骨骼形态；若业务上只关心活体，可在下一版拆为“生物残片”。
4. 三大类模型训练时必须沿用原始 train/val/test 划分，禁止重新随机拆分，以避免同一采样批次或近似图像泄漏到验证集与测试集。

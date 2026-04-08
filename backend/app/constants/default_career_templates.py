"""预置职业模板数据 - 按小说类型分类"""

# 预置职业模板数据
# 每种类型包含3个主职业和2个副职业
DEFAULT_CAREER_TEMPLATES = [
    # ==================== 修仙类 ====================
    {
        "name": "剑修",
        "type": "main",
        "description": "以剑入道的修炼者，主修剑意，攻击凌厉，杀伐果断。剑修追求人剑合一，以剑证道。",
        "category": "战斗系",
        "applicable_genres": ["修仙", "仙侠"],
        "stages": [
            {"level": 1, "name": "炼气期", "description": "初识剑道，凝聚剑气"},
            {"level": 2, "name": "筑基期", "description": "剑基初成，剑气护体"},
            {"level": 3, "name": "金丹期", "description": "剑丹合一，剑意初生"},
            {"level": 4, "name": "元婴期", "description": "剑婴凝聚，剑意成形"},
            {"level": 5, "name": "化神期", "description": "剑心通明，剑域初展"},
            {"level": 6, "name": "炼虚期", "description": "虚空剑道，剑意破空"},
            {"level": 7, "name": "合体期", "description": "人剑合一，剑道大成"},
            {"level": 8, "name": "大乘期", "description": "剑道圆满，万剑归宗"},
            {"level": 9, "name": "渡劫期", "description": "剑劫临身，剑道超脱"},
            {"level": 10, "name": "仙人", "description": "剑仙成就，剑道永恒"}
        ],
        "max_stage": 10,
        "requirements": "需有剑道天赋，心志坚定",
        "special_abilities": "剑气外放、御剑飞行、剑域镇压",
        "worldview_rules": "契合修仙世界剑道法则",
        "base_attributes": {"灵力": 60, "悟性": 70, "气运": 50},
        "per_stage_bonus": {"灵力": {"per_stage": 100}, "悟性": {"per_stage": 5}},
        "is_official": True,
        "order_index": 1
    },
    {
        "name": "法修",
        "type": "main",
        "description": "专修法术神通的修炼者，精通各类法术，攻击手段多变，擅长远程战斗和群体攻击。",
        "category": "法术系",
        "applicable_genres": ["修仙", "仙侠"],
        "stages": [
            {"level": 1, "name": "炼气期", "description": "感应天地灵气"},
            {"level": 2, "name": "筑基期", "description": "筑建道基"},
            {"level": 3, "name": "金丹期", "description": "凝聚金丹"},
            {"level": 4, "name": "元婴期", "description": "元婴出窍"},
            {"level": 5, "name": "化神期", "description": "神识化形"},
            {"level": 6, "name": "炼虚期", "description": "炼虚合道"},
            {"level": 7, "name": "合体期", "description": "天人合一"},
            {"level": 8, "name": "大乘期", "description": "法力无边"},
            {"level": 9, "name": "渡劫期", "description": "渡劫飞升"},
            {"level": 10, "name": "仙人", "description": "得道成仙"}
        ],
        "max_stage": 10,
        "requirements": "灵根纯正，悟性较高",
        "special_abilities": "五行法术、神通术法、阵法布置",
        "worldview_rules": "契合修仙世界法道法则",
        "base_attributes": {"灵力": 80, "悟性": 65, "气运": 50},
        "per_stage_bonus": {"灵力": {"per_stage": 120}, "悟性": {"per_stage": 3}},
        "is_official": True,
        "order_index": 2
    },
    {
        "name": "体修",
        "type": "main",
        "description": "以肉身为器的修炼者，淬炼体魄，力大无穷，防御惊人，近战无敌。",
        "category": "战斗系",
        "applicable_genres": ["修仙", "玄幻"],
        "stages": [
            {"level": 1, "name": "锻体期", "description": "初锻肉身"},
            {"level": 2, "name": "练脏期", "description": "强化脏腑"},
            {"level": 3, "name": "换血期", "description": "血脉蜕变"},
            {"level": 4, "name": "金身期", "description": "肉身成圣"},
            {"level": 5, "name": "法身期", "description": "凝聚法相"},
            {"level": 6, "name": "真身期", "description": "真身不灭"},
            {"level": 7, "name": "神体期", "description": "神体大成"},
            {"level": 8, "name": "圣体期", "description": "圣体无敌"},
            {"level": 9, "name": "帝体期", "description": "帝体临世"},
            {"level": 10, "name": "道体期", "description": "肉身证道"}
        ],
        "max_stage": 10,
        "requirements": "体魄强健，意志坚韧",
        "special_abilities": "金刚不坏、力破万法、肉身成圣",
        "worldview_rules": "契合修仙/玄幻体修之道",
        "base_attributes": {"灵力": 50, "悟性": 50, "气运": 50},
        "per_stage_bonus": {"灵力": {"per_stage": 80}, "悟性": {"per_stage": 2}},
        "is_official": True,
        "order_index": 3
    },
    {
        "name": "炼丹师",
        "type": "sub",
        "description": "精通丹道炼制的修士，能够炼制各类丹药，提升修为，治疗伤势，是各大势力争相拉拢的对象。",
        "category": "生产系",
        "applicable_genres": ["修仙", "仙侠", "玄幻"],
        "stages": [
            {"level": 1, "name": "学徒", "description": "识药辨材"},
            {"level": 2, "name": "入门", "description": "初试炼丹"},
            {"level": 3, "name": "熟练", "description": "丹成无暇"},
            {"level": 4, "name": "精通", "description": "丹药精纯"},
            {"level": 5, "name": "大师", "description": "丹道大成"}
        ],
        "max_stage": 5,
        "requirements": "火灵根为佳，悟性高",
        "special_abilities": "丹药炼制、药性辨识、丹方创新",
        "worldview_rules": "丹道为修仙百艺之首",
        "base_attributes": {"悟性": 70, "气运": 55},
        "per_stage_bonus": {"悟性": {"per_stage": 5}},
        "is_official": True,
        "order_index": 101
    },
    {
        "name": "炼器师",
        "type": "sub",
        "description": "精通器道锻造的修士，能够打造各类法宝、灵器、神兵，是宗门实力的重要保障。",
        "category": "生产系",
        "applicable_genres": ["修仙", "仙侠", "玄幻"],
        "stages": [
            {"level": 1, "name": "学徒", "description": "识材辨矿"},
            {"level": 2, "name": "入门", "description": "初试锻造"},
            {"level": 3, "name": "熟练", "description": "器成有灵"},
            {"level": 4, "name": "精通", "description": "法宝出炉"},
            {"level": 5, "name": "大师", "description": "器道大成"}
        ],
        "max_stage": 5,
        "requirements": "金灵根为佳，心思细腻",
        "special_abilities": "法宝锻造、器灵培养、禁制铭刻",
        "worldview_rules": "器道与丹道并称修仙两大辅道",
        "base_attributes": {"悟性": 65, "气运": 55},
        "per_stage_bonus": {"悟性": {"per_stage": 4}},
        "is_official": True,
        "order_index": 102
    },

    # ==================== 玄幻类 ====================
    {
        "name": "斗者",
        "type": "main",
        "description": "修炼斗气以战斗为主的武者，拥有强大的战斗本能和各种斗技，是玄幻世界最常见的战斗职业。",
        "category": "战斗系",
        "applicable_genres": ["玄幻"],
        "stages": [
            {"level": 1, "name": "凡人", "description": "初识斗气"},
            {"level": 2, "name": "斗者", "description": "凝聚斗气"},
            {"level": 3, "name": "斗师", "description": "斗气化形"},
            {"level": 4, "name": "大斗师", "description": "斗气铠甲"},
            {"level": 5, "name": "斗灵", "description": "斗气凝物"},
            {"level": 6, "name": "斗王", "description": "斗气化翼"},
            {"level": 7, "name": "斗皇", "description": "斗气巅峰"},
            {"level": 8, "name": "斗宗", "description": "空间之力"},
            {"level": 9, "name": "斗尊", "description": "尊者之境"},
            {"level": 10, "name": "斗圣", "description": "圣者无敌"}
        ],
        "max_stage": 10,
        "requirements": "斗气天赋，意志坚定",
        "special_abilities": "斗技释放、斗气外放、战斗直觉",
        "worldview_rules": "契合玄幻斗气体系",
        "base_attributes": {"斗气": 70, "天赋": 60},
        "per_stage_bonus": {"斗气": {"per_stage": 50}, "天赋": {"per_stage": 3}},
        "is_official": True,
        "order_index": 11
    },
    {
        "name": "血脉武者",
        "type": "main",
        "description": "觉醒远古血脉的武者，拥有强大血脉之力，能够施展血脉神通，是天赋最强的战斗者。",
        "category": "战斗系",
        "applicable_genres": ["玄幻"],
        "stages": [
            {"level": 1, "name": "血脉觉醒", "description": "初觉醒血脉"},
            {"level": 2, "name": "血脉初成", "description": "血脉之力显现"},
            {"level": 3, "name": "血脉凝练", "description": "血脉力量增强"},
            {"level": 4, "name": "血脉蜕变", "description": "血脉品质提升"},
            {"level": 5, "name": "血脉大成", "description": "血脉神通觉醒"},
            {"level": 6, "name": "血脉返祖", "description": "返祖血脉之力"},
            {"level": 7, "name": "血脉称王", "description": "血脉之王"},
            {"level": 8, "name": "血脉称皇", "description": "血脉皇者"},
            {"level": 9, "name": "血脉称帝", "description": "血脉帝者"},
            {"level": 10, "name": "血脉至尊", "description": "血脉至尊"}
        ],
        "max_stage": 10,
        "requirements": "需有血脉天赋，远古血脉传承",
        "special_abilities": "血脉神通、血脉压制、血脉传承",
        "worldview_rules": "契合玄幻血脉体系",
        "base_attributes": {"斗气": 60, "天赋": 80},
        "per_stage_bonus": {"斗气": {"per_stage": 60}, "天赋": {"per_stage": 5}},
        "is_official": True,
        "order_index": 12
    },

    # ==================== 武侠类 ====================
    {
        "name": "剑客",
        "type": "main",
        "description": "以剑为生的江湖人士，剑法高超，快意恩仇，行走江湖以剑明志。",
        "category": "战斗系",
        "applicable_genres": ["武侠"],
        "stages": [
            {"level": 1, "name": "初入江湖", "description": "初学剑法"},
            {"level": 2, "name": "江湖小辈", "description": "剑法入门"},
            {"level": 3, "name": "江湖名宿", "description": "剑法小成"},
            {"level": 4, "name": "一方豪杰", "description": "剑法大成"},
            {"level": 5, "name": "武林高手", "description": "剑法精深"},
            {"level": 6, "name": "绝顶高手", "description": "剑法化境"},
            {"level": 7, "name": "一代宗师", "description": "开宗立派"},
            {"level": 8, "name": "武林盟主", "description": "武林至尊"},
            {"level": 9, "name": "武道圣人", "description": "武道巅峰"},
            {"level": 10, "name": "传说", "description": "剑仙传说"}
        ],
        "max_stage": 10,
        "requirements": "剑道天赋，悟性较高",
        "special_abilities": "剑法绝学、轻功身法、剑气御敌",
        "worldview_rules": "契合武侠江湖体系",
        "base_attributes": {"内力": 60, "武功": 70, "身法": 60},
        "per_stage_bonus": {"内力": {"per_stage": 30}, "武功": {"per_stage": 5}},
        "is_official": True,
        "order_index": 21
    },
    {
        "name": "名医",
        "type": "sub",
        "description": "精通医术的江湖人士，能够救治伤患、炼制丹药，是江湖中不可或缺的存在。",
        "category": "辅助系",
        "applicable_genres": ["武侠", "修仙"],
        "stages": [
            {"level": 1, "name": "学徒", "description": "识药辨症"},
            {"level": 2, "name": "入门", "description": "初试治病"},
            {"level": 3, "name": "熟练", "description": "妙手回春"},
            {"level": 4, "name": "精通", "description": "药到病除"},
            {"level": 5, "name": "神医", "description": "医术通神"}
        ],
        "max_stage": 5,
        "requirements": "医者仁心，记忆力强",
        "special_abilities": "医术救人、丹药炼制、毒术辨识",
        "worldview_rules": "医者仁心，济世救人",
        "base_attributes": {"内力": 40, "武功": 30, "身法": 40},
        "per_stage_bonus": {"内力": {"per_stage": 10}},
        "is_official": True,
        "order_index": 201
    },

    # ==================== 都市类 ====================
    {
        "name": "企业家",
        "type": "main",
        "description": "商业精英，掌控企业命脉，拥有强大的商业头脑和人脉资源。",
        "category": "商业系",
        "applicable_genres": ["都市", "言情"],
        "stages": [
            {"level": 1, "name": "普通", "description": "初入职场"},
            {"level": 2, "name": "小康", "description": "事业起步"},
            {"level": 3, "name": "中产", "description": "事业有成"},
            {"level": 4, "name": "富裕", "description": "财富自由"},
            {"level": 5, "name": "精英", "description": "商业精英"},
            {"level": 6, "name": "顶层", "description": "行业领袖"}
        ],
        "max_stage": 6,
        "requirements": "商业头脑，人际交往能力",
        "special_abilities": "商业谈判、资源整合、企业管理",
        "worldview_rules": "现代商业社会",
        "base_attributes": {"智力": 70, "魅力": 60, "财富": 80, "社交": 70},
        "per_stage_bonus": {"财富": {"per_stage": 100}, "社交": {"per_stage": 5}},
        "is_official": True,
        "order_index": 31
    },
    {
        "name": "医生",
        "type": "main",
        "description": "救死扶伤的医者，拥有精湛的医术和高尚的职业道德。",
        "category": "专业系",
        "applicable_genres": ["都市", "言情"],
        "stages": [
            {"level": 1, "name": "普通", "description": "医学院学生"},
            {"level": 2, "name": "小康", "description": "住院医师"},
            {"level": 3, "name": "中产", "description": "主治医师"},
            {"level": 4, "name": "富裕", "description": "副主任医师"},
            {"level": 5, "name": "精英", "description": "主任医师"},
            {"level": 6, "name": "顶层", "description": "医学专家"}
        ],
        "max_stage": 6,
        "requirements": "医者仁心，学习能力强",
        "special_abilities": "医术精湛、临床诊断、医学研究",
        "worldview_rules": "现代医疗体系",
        "base_attributes": {"智力": 80, "魅力": 60, "财富": 50, "社交": 50},
        "per_stage_bonus": {"智力": {"per_stage": 5}, "财富": {"per_stage": 50}},
        "is_official": True,
        "order_index": 32
    },

    # ==================== 科幻类 ====================
    {
        "name": "基因战士",
        "type": "main",
        "description": "经过基因改造的超级战士，拥有远超常人的身体素质和战斗能力。",
        "category": "战斗系",
        "applicable_genres": ["科幻"],
        "stages": [
            {"level": 1, "name": "E级", "description": "初步基因改造"},
            {"level": 2, "name": "D级", "description": "基因强化"},
            {"level": 3, "name": "C级", "description": "基因变异"},
            {"level": 4, "name": "B级", "description": "基因进化"},
            {"level": 5, "name": "A级", "description": "基因觉醒"},
            {"level": 6, "name": "S级", "description": "基因领域"},
            {"level": 7, "name": "SS级", "description": "基因大师"},
            {"level": 8, "name": "SSS级", "description": "基因传奇"},
            {"level": 9, "name": "X级", "description": "基因超凡"},
            {"level": 10, "name": "神级", "description": "基因神化"}
        ],
        "max_stage": 10,
        "requirements": "基因适配度高",
        "special_abilities": "超级力量、再生能力、战斗本能",
        "worldview_rules": "基因改造科技体系",
        "base_attributes": {"战斗力": 1500, "技术能力": 40},
        "per_stage_bonus": {"战斗力": {"per_stage": 500}, "技术能力": {"per_stage": 3}},
        "is_official": True,
        "order_index": 41
    },
    {
        "name": "机甲师",
        "type": "main",
        "description": "驾驶机甲作战的精英战士，精通机甲操控和战术配合。",
        "category": "战斗系",
        "applicable_genres": ["科幻"],
        "stages": [
            {"level": 1, "name": "E级", "description": "机甲学徒"},
            {"level": 2, "name": "D级", "description": "机甲驾驶员"},
            {"level": 3, "name": "C级", "description": "机甲精英"},
            {"level": 4, "name": "B级", "description": "机甲王牌"},
            {"level": 5, "name": "A级", "description": "机甲大师"},
            {"level": 6, "name": "S级", "description": "机甲传奇"},
            {"level": 7, "name": "SS级", "description": "机甲至尊"},
            {"level": 8, "name": "SSS级", "description": "机甲神话"},
            {"level": 9, "name": "X级", "description": "机甲超凡"},
            {"level": 10, "name": "神级", "description": "机甲之神"}
        ],
        "max_stage": 10,
        "requirements": "神经连接适配度高，反应速度快",
        "special_abilities": "机甲操控、战术指挥、机甲改装",
        "worldview_rules": "机甲科技体系",
        "base_attributes": {"战斗力": 1200, "技术能力": 70},
        "per_stage_bonus": {"战斗力": {"per_stage": 400}, "技术能力": {"per_stage": 5}},
        "is_official": True,
        "order_index": 42
    },

    # ==================== 奇幻类 ====================
    {
        "name": "法师",
        "type": "main",
        "description": "掌控魔法之力的施法者，能够施展各种元素魔法，拥有强大的远程攻击能力。",
        "category": "法术系",
        "applicable_genres": ["奇幻"],
        "stages": [
            {"level": 1, "name": "学徒", "description": "初学魔法"},
            {"level": 2, "name": "初级", "description": "魔法入门"},
            {"level": 3, "name": "中级", "description": "魔法小成"},
            {"level": 4, "name": "高级", "description": "魔法大成"},
            {"level": 5, "name": "大师", "description": "魔法精深"},
            {"level": 6, "name": "宗师", "description": "魔法化境"},
            {"level": 7, "name": "传奇", "description": "传奇法师"},
            {"level": 8, "name": "史诗", "description": "史诗法师"},
            {"level": 9, "name": "神话", "description": "神话法师"},
            {"level": 10, "name": "半神", "description": "半神法师"}
        ],
        "max_stage": 10,
        "requirements": "魔法天赋，感知力强",
        "special_abilities": "元素魔法、魔法阵列、魔法物品制作",
        "worldview_rules": "魔法能量体系",
        "base_attributes": {"魔力": 80, "感知": 70},
        "per_stage_bonus": {"魔力": {"per_stage": 100}, "感知": {"per_stage": 4}},
        "is_official": True,
        "order_index": 51
    },
    {
        "name": "战士",
        "type": "main",
        "description": "以力量和武技为主的近战职业，拥有强大的防御力和近身战斗力。",
        "category": "战斗系",
        "applicable_genres": ["奇幻"],
        "stages": [
            {"level": 1, "name": "学徒", "description": "初学武技"},
            {"level": 2, "name": "初级", "description": "武技入门"},
            {"level": 3, "name": "中级", "description": "武技小成"},
            {"level": 4, "name": "高级", "description": "武技大成"},
            {"level": 5, "name": "大师", "description": "武技精深"},
            {"level": 6, "name": "宗师", "description": "武技化境"},
            {"level": 7, "name": "传奇", "description": "传奇战士"},
            {"level": 8, "name": "史诗", "description": "史诗战士"},
            {"level": 9, "name": "神话", "description": "神话战士"},
            {"level": 10, "name": "半神", "description": "半神战士"}
        ],
        "max_stage": 10,
        "requirements": "力量天赋，体质强健",
        "special_abilities": "重型武器精通、坚韧防御、狂暴战斗",
        "worldview_rules": "战士荣耀体系",
        "base_attributes": {"魔力": 30, "感知": 40},
        "per_stage_bonus": {"魔力": {"per_stage": 20}, "感知": {"per_stage": 2}},
        "is_official": True,
        "order_index": 52
    },

    # ==================== 历史类 ====================
    {
        "name": "武将",
        "type": "main",
        "description": "沙场点兵的武将，精通兵法和武艺，是战场上的定海神针。",
        "category": "军事系",
        "applicable_genres": ["历史"],
        "stages": [
            {"level": 1, "name": "平民", "description": "布衣之身"},
            {"level": 2, "name": "秀才", "description": "初有功名"},
            {"level": 3, "name": "举人", "description": "科举中式"},
            {"level": 4, "name": "进士", "description": "金榜题名"},
            {"level": 5, "name": "翰林", "description": "翰林学士"},
            {"level": 6, "name": "知县", "description": "一县父母"},
            {"level": 7, "name": "知府", "description": "一方大员"},
            {"level": 8, "name": "巡抚", "description": "封疆大吏"},
            {"level": 9, "name": "总督", "description": "督抚一方"},
            {"level": 10, "name": "宰相", "description": "位极人臣"}
        ],
        "max_stage": 10,
        "requirements": "武艺高强，兵法精通",
        "special_abilities": "领兵打仗、武艺绝伦、兵法韬略",
        "worldview_rules": "古代军事体系",
        "base_attributes": {"武艺": 80, "谋略": 60, "声望": 50},
        "per_stage_bonus": {"武艺": {"per_stage": 5}, "声望": {"per_stage": 8}},
        "is_official": True,
        "order_index": 61
    },
    {
        "name": "谋士",
        "type": "main",
        "description": "运筹帷幄的智囊，精通谋略和治国之道，是君王的重要辅佐。",
        "category": "谋略系",
        "applicable_genres": ["历史"],
        "stages": [
            {"level": 1, "name": "平民", "description": "布衣之士"},
            {"level": 2, "name": "秀才", "description": "初有才名"},
            {"level": 3, "name": "举人", "description": "声名鹊起"},
            {"level": 4, "name": "进士", "description": "名动京华"},
            {"level": 5, "name": "翰林", "description": "清贵之职"},
            {"level": 6, "name": "知县", "description": "初涉仕途"},
            {"level": 7, "name": "知府", "description": "治理有方"},
            {"level": 8, "name": "巡抚", "description": "一方重臣"},
            {"level": 9, "name": "总督", "description": "国之栋梁"},
            {"level": 10, "name": "宰相", "description": "一人之下"}
        ],
        "max_stage": 10,
        "requirements": "智慧过人，精通经史",
        "special_abilities": "运筹帷幄、治国安邦、外交辞令",
        "worldview_rules": "古代文官体系",
        "base_attributes": {"武艺": 30, "谋略": 90, "声望": 60},
        "per_stage_bonus": {"谋略": {"per_stage": 5}, "声望": {"per_stage": 6}},
        "is_official": True,
        "order_index": 62
    },

    # ==================== 悬疑类 ====================
    {
        "name": "刑侦专家",
        "type": "main",
        "description": "精通犯罪心理学和刑侦技术的破案专家，能够从蛛丝马迹中找到真相。",
        "category": "侦查系",
        "applicable_genres": ["悬疑"],
        "stages": [
            {"level": 1, "name": "新手", "description": "初入刑侦"},
            {"level": 2, "name": "入门", "description": "掌握基本技能"},
            {"level": 3, "name": "熟练", "description": "独立办案"},
            {"level": 4, "name": "专家", "description": "业界认可"},
            {"level": 5, "name": "大师", "description": "破案如神"},
            {"level": 6, "name": "神探", "description": "传奇神探"}
        ],
        "max_stage": 6,
        "requirements": "观察力敏锐，逻辑思维强",
        "special_abilities": "犯罪侧写、证据分析、审讯技巧",
        "worldview_rules": "现代刑侦体系",
        "base_attributes": {"推理能力": 80, "观察力": 75, "心理素质": 70, "人脉": 50},
        "per_stage_bonus": {"推理能力": {"per_stage": 5}, "观察力": {"per_stage": 4}},
        "is_official": True,
        "order_index": 71
    },
    {
        "name": "私家侦探",
        "type": "main",
        "description": "独立执业的侦探，接受各种委托调查，行走在灰色地带的真相追寻者。",
        "category": "侦查系",
        "applicable_genres": ["悬疑"],
        "stages": [
            {"level": 1, "name": "新手", "description": "初出茅庐"},
            {"level": 2, "name": "入门", "description": "小有名气"},
            {"level": 3, "name": "熟练", "description": "委托不断"},
            {"level": 4, "name": "专家", "description": "业界知名"},
            {"level": 5, "name": "大师", "description": "名侦探"},
            {"level": 6, "name": "神探", "description": "传奇侦探"}
        ],
        "max_stage": 6,
        "requirements": "观察力强，人际交往能力佳",
        "special_abilities": "跟踪调查、情报收集、伪装潜入",
        "worldview_rules": "现代侦探体系",
        "base_attributes": {"推理能力": 70, "观察力": 80, "心理素质": 65, "人脉": 70},
        "per_stage_bonus": {"观察力": {"per_stage": 5}, "人脉": {"per_stage": 5}},
        "is_official": True,
        "order_index": 72
    },

    # ==================== 言情类 ====================
    {
        "name": "总裁",
        "type": "main",
        "description": "商业帝国的掌控者，权力与财富的象征，霸道与温柔并存。",
        "category": "商业系",
        "applicable_genres": ["言情", "都市"],
        "stages": [
            {"level": 1, "name": "普通", "description": "家族子弟"},
            {"level": 2, "name": "小康", "description": "事业起步"},
            {"level": 3, "name": "中产", "description": "独立发展"},
            {"level": 4, "name": "富裕", "description": "商业精英"},
            {"level": 5, "name": "精英", "description": "商业巨头"},
            {"level": 6, "name": "顶层", "description": "商业帝王"}
        ],
        "max_stage": 6,
        "requirements": "家族背景或个人能力出众",
        "special_abilities": "商业谈判、资源整合、魅力非凡",
        "worldview_rules": "现代都市言情",
        "base_attributes": {"魅力": 90, "情商": 70, "家境": 95, "才华": 60},
        "per_stage_bonus": {"魅力": {"per_stage": 3}, "家境": {"per_stage": 10}},
        "is_official": True,
        "order_index": 81
    },
    {
        "name": "设计师",
        "type": "sub",
        "description": "才华横溢的创意设计师，用设计诠释美学与生活。",
        "category": "创意系",
        "applicable_genres": ["言情", "都市"],
        "stages": [
            {"level": 1, "name": "普通", "description": "设计学生"},
            {"level": 2, "name": "小康", "description": "初级设计师"},
            {"level": 3, "name": "中产", "description": "资深设计师"},
            {"level": 4, "name": "富裕", "description": "设计总监"},
            {"level": 5, "name": "精英", "description": "知名设计师"}
        ],
        "max_stage": 5,
        "requirements": "艺术天赋，创意思维",
        "special_abilities": "设计创作、审美独到、艺术感知",
        "worldview_rules": "现代创意产业",
        "base_attributes": {"魅力": 75, "情商": 60, "家境": 40, "才华": 85},
        "per_stage_bonus": {"才华": {"per_stage": 5}},
        "is_official": True,
        "order_index": 801
    }
]


def get_templates_for_genre(genre: str) -> list:
    """
    获取指定小说类型的职业模板

    Args:
        genre: 小说类型

    Returns:
        匹配的职业模板列表
    """
    return [
        template for template in DEFAULT_CAREER_TEMPLATES
        if genre in template.get("applicable_genres", [])
    ]


def get_all_official_templates() -> list:
    """获取所有官方预置模板"""
    return [t for t in DEFAULT_CAREER_TEMPLATES if t.get("is_official", False)]
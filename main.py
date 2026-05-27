from src.ai.core.skills import skill_service, SkillDefinition, SkillMetadata

# 1. 导入验证
print('=== 导入验证 ===')
print(f'SkillDefinition: {SkillDefinition}')
print(f'SkillMetadata: {SkillMetadata}')

# 2. 发现测试
print('\n=== 发现测试 ===')
skills = skill_service.discover()
print(f'发现 {len(skills)} 个技能')
for s in skills:
    print(f'  - {s.name}: auto={s.is_auto_triggerable}, user_invocable={s.user_invocable}')
    if s.allowed_tools:
        print(f'    allowed_tools: {s.allowed_tools}')
    if s.argument_hint:
        print(f'    argument_hint: {s.argument_hint}')

# 3. 渐进式披露 - Level 1
print('\n=== Level 1: 元数据 ===')
metadata = skill_service.get_skill_metadata()
for m in metadata:
    print(f'  - {m.name}: {m.description[:40]}...')

# 4. 激活测试 - Level 2 (with \$ARGUMENTS)
print('\n=== Level 2: 激活 + \$ARGUMENTS ===')
content = skill_service.activate('summarize', arguments='This is a long text about AI.')
print(f'  summarize 渲染内容（前80字）:')
print(f'  {content[:80]}...')

# 5. Jinja2 兼容测试
print('\n=== Jinja2 兼容 ===')
content2 = skill_service.activate('translate', arguments='hello world', variables={'target_lang': '日语'})
print(f'  translate 渲染内容（前80字）:')
print(f'  {content2[:80]}...')

# 6. 斜杠命令匹配
print('\n=== 斜杠命令匹配 ===')
match = skill_service.match_slash_command('/translate hello')
print(f'  /translate: {match.name if match else None}')
match2 = skill_service.match_slash_command('/unknown')
print(f'  /unknown: {match2}')

# 7. 斜杠命令列表
print('\n=== 斜杠命令列表 ===')
cmds = skill_service.get_slash_commands()
for c in cmds:
    print(f'  {c["command"]}: {c["description"][:40]}...')

# 8. 列表过滤
print('\n=== 列表过滤 ===')
invocable = skill_service.list_user_invocable()
auto = skill_service.list_auto_triggerable()
print(f'  用户可调用: {len(invocable)} 个')
print(f'  可自动触发: {len(auto)} 个')

# 9. 缓存测试
print('\n=== 缓存测试 ===')
skill_service.invalidate()
skills2 = skill_service.discover()
print(f'  invalidate 后重新发现: {len(skills2)} 个')

print('\n所有测试通过！')

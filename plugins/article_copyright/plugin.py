from djangoblog.plugin_manage.base_plugin import BasePlugin
from djangoblog.plugin_manage import hooks
from djangoblog.plugin_manage.hook_constants import ARTICLE_CONTENT_HOOK_NAME


class ArticleCopyrightPlugin(BasePlugin):
    PLUGIN_NAME = '文章结尾版权声明'
    PLUGIN_DESCRIPTION = '一个在文章正文末尾添加版权声明的插件。'
    PLUGIN_VERSION = '0.2.0'
    PLUGIN_AUTHOR = 'liangliangyy'

    # 2. 实现 register_hooks 方法，专门用于注册钩子
    def register_hooks(self):
        # 在这里将插件的方法注册到指定的钩子上
        hooks.register(ARTICLE_CONTENT_HOOK_NAME, self.add_copyright_to_content)

    def add_copyright_to_content(self, content, *args, **kwargs):
        return content


# 3. 实例化插件。
# 这会自动调用 BasePlugin.__init__，然后 BasePlugin.__init__ 会调用我们上面定义的 register_hooks 方法。
plugin = ArticleCopyrightPlugin()

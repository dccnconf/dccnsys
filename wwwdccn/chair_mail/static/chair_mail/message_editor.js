$.fn.messageEditor = function ({textarea}) {
  const components = {
    editor: undefined,
  };

  const api = {
    insertText: (text, newLine = false, offset = undefined) => {
      const doc = components.editor.getDoc();
      const cursor = doc.getCursor();
      if (doc.somethingSelected()) {
        console.log('something selected!');
      } else {
        const prefix = newLine && cursor.ch > 0 ? '\n' : '';
        doc.replaceRange(`${prefix}${text}`, cursor);
        if (offset !== undefined)
          doc.setCursor({ch: cursor.ch + offset, line: cursor.line});
      }
      components.editor.focus();
    },

    initialize: () => {
      // 1) Create CodeMirror editor
      requirejs([
        'codemirror/lib/codemirror',
        'codemirror/mode/markdown/markdown',
        'codemirror/addon/scroll/simplescrollbars'
      ], function (CodeMirror) {
        components.editor = CodeMirror.fromTextArea(textarea, {
          mode: 'markdown',
          theme: 'monokai',
          highlightFormatting: true,
          scrollbarStyle: "simple",
          lineWrapping: true,
        });
      });

      // 2) Bind buttons:
      $('.message-editor-insert-text').on('click', event => {
        const btn = $(event.currentTarget);
        const newLine = btn.attr('data-newline') === '1';
        const offset = btn.is('[data-offset]') ? Number(btn.attr('data-offset')) : undefined;
        api.insertText(btn.attr('data-text'), newLine, offset);
      });

    },
  };

  api.initialize();

  return {
    getCM: () => { return components['editor']; }
    // initialize: api.initialize,
  }
};

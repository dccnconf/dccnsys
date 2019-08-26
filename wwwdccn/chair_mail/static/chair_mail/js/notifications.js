/*
 **************************************************************************
 * HELPERS
 **************************************************************************
 */
// Based on answer on StackOverflow: https://stackoverflow.com/a/7592235
const addClassOnce = function (elem, klass) {
  if (!elem.hasClass(klass)) elem.addClass(klass);
};


const renderSelect = function (select, objects, emptyOptionName = 'select value') {
  const prevID = select.val();
  const items = [`<option value="">${emptyOptionName}</option>`];
  items.push(...objects.map(object => `<option value="${object.id}">${object.name} (ID: ${object.id})</option>`));
  select.html(Object.values(items).join(''));
  const nextID = objects.filter(o => String(o.id) === prevID).length === 0 ? '' : prevID;
  if (nextID !== prevID)
    select.change();
  select.val(nextID);
};

/*
 **************************************************************************
 * MODELS AND DATA MANAGERS
 **************************************************************************
 */
/**
 * Data manager for users/submissions. Provides API for loading data.
 *
 * @param listObjectsURL: a URL to send HTTP GET request to for reading the list of objects (users or submissions)
 * @param onLoaded: optional handler without arguments, called when the model loads all data from the server
 *
 * (!!) IMPORTANT NOTE: for now, we load all objects in single AJAX query. In future, we should do something with this.
 */
const Model = function ({listObjectsURL, onLoaded=()=>{}}) {
  const state = {
    objects: {},  // id -> [submission|user]
    objectType: undefined,
  };

  const api = {
    createUserFromJSON: object => {
      return {
        object_type: 'user',
        id: object['id'],
        name: object['name'],
      };
      },

    createSubmissionFromJSON: object => {
      return {
        object_type: 'submission',
        id: object['id'],
        name: object['title'],
        authors: object['authors'].map(author => {
          return {id: author['id'], name: author['name']};
        }),
      };
      },

    createObjectFromJSON: (type, object) => {
      if (type === 'user')
        return api.createUserFromJSON(object);
      else if (type === 'submission')
        return api.createSubmissionFromJSON(object);
      throw `unrecognized object type "${type}`;
      },

    loadObjects: (url, onFinish = undefined) => {
      $.get(url, data => {
        const type = data['type'];
        let container;
        state.objects = [];
        state.objectType = type;
        data['objects'].forEach(receivedObject => {
          const object = api.createObjectFromJSON(type, receivedObject);
          state.objects[object['id']] = object;
        });
        if (onFinish !== undefined)
          onFinish();
      });
    },
    /** Load lists and users into `state`, bind lists to users */
    load: (success=undefined) => {
      api.loadObjects(listObjectsURL, () => {
        if (success) success();
      });
    },

    /** Initialization */
    initialize: () => {
      api.load(onLoaded);
    },
  };

  //
  // PUBLIC API
  //
  return {
    initialize: api.initialize,
    get: id => state.objects[id],
    all: () => Object.values(state.objects),
  };
};


/*
 **************************************************************************
 * VIEW CONTROLLERS
 **************************************************************************
 */
const submitPreviewForm = function ({form, validate, subject, body, previewArea}) {
  if (validate()) {
    const formData = form.serializeArray();
    formData.push({name: 'body', value: body});
    formData.push({name: 'subject', value: subject});
    $.get(form.attr('action'), formData, data => {
      previewArea.render(data);
    });
  } else {
    previewArea.render({subject: '', body: ''});
  }
  return false;  // to prevent submitting in normal way
};


$.fn.previewSubmissionForm = function ({getObjects, getSubmission, getBody, getSubject, getPreviewArea}) {
  const elements = {
    submissionSelect: this.find('select[name="submission"]'),
    userSelect: this.find('select[name="user"]'),
  };

  const api = {
    update: () => {
      renderSelect(elements.submissionSelect, getObjects(), 'Select submission');
      },

    validateInput: () => {
      let result = true;
      [elements.submissionSelect, elements.userSelect].forEach(select => {
        if (select.val() === '') {
          addClassOnce(select, 'is-invalid');
          result = false;
        } else {
          select.removeClass('is-invalid');
        }
      });
      return result;
      },

    initialize: () => {
      // Render options:
      elements.submissionSelect.on('change', () => {
        const subID = elements.submissionSelect.val();
        let users = [];
        if (subID !== '') {
          users = getSubmission(subID).authors;
        }
        renderSelect(elements.userSelect, users, 'Select user');
      });

      this.on('submit', () => submitPreviewForm({
        form: this, validate: api.validateInput, subject: getSubject(), body: getBody(),
        previewArea: getPreviewArea()
      }));

      api.update();
    },
  };

  api.initialize();
  return {
    update: api.update,
  }
};


$.fn.previewUserForm = function ({getObjects, getBody, getSubject, getPreviewArea}) {
  const elements = {
    userSelect: this.find('select[name="user"]'),
  };

  const api = {
    update: () => {
      renderSelect(elements.userSelect, getObjects(), 'Select user');
      },

    validateInput: () => {
      if (elements.userSelect.val() === '') {
        addClassOnce(elements.userSelect, 'is-invalid');
        return false;
      }
      elements.userSelect.removeClass('is-invalid');
      return true;
      },

    initialize: () => {
      this.on('submit', () => submitPreviewForm({
        form: this, validate: api.validateInput, subject: getSubject(), body: getBody(),
        previewArea: getPreviewArea()
      }));

      api.update();
    },
  };

  api.initialize();
  return {
    update: api.update,
  }
};


$.fn.previewArea = function ({}) {
  const elements = {
    previewSubjectField: this.find('.preview-message-subject'),
    previewBodyField: this.find('.preview-message-body')
  };

  const api = {
    render: (subject, body) => {
      elements.previewSubjectField.text(subject);
      elements.previewBodyField.html(body);
    },
  };

  return {
    render: ({subject, body}) => api.render(subject, body),
  }
};


/**************************************************************************
 * CONTROLLER
 *************************************************************************/
const controller = (function () {
  const state = {
    model: undefined,
  };

  let elements = undefined;

  const components = {
    previewForm: undefined,
    previewArea: undefined,
    editor: undefined,
  };

  const loadElements = () => {
    return {
      messageEditor: $('.message-editor'),
      subjectInput: $('#id_subject'),
      previewForm: $('.preview-form'),
      previewArea: $('.preview-message'),
      previewTab: $('#preview-tab'),
      updatePreviewBtn: $('#updatePreviewBtn'),
    }
  };

  return {
    initialize: function () {
      // 0) Load all page elements:
      elements = loadElements();

      // 1) Create the editor. It will be used by other components, so we need to instantiate it prior to other parts:
      components.editor = elements.messageEditor.messageEditor({
        textarea: $('#id_body')[0],
      });

      // 2) Build the model, and create other components when data is loaded:
      state.model = Model({
        listObjectsURL: elements.previewTab.attr('data-objects-url'),
        onLoaded: () => {
          // 2.1) Create preview selector form component:
          if (elements.previewForm.is('.preview-submission-form')) {
            components.previewForm = elements.previewForm.previewSubmissionForm({
              getObjects: state.model.all,
              getSubmission: state.model.get,
              getBody: () => components.editor.getCM().getValue(),
              getSubject: () => elements.subjectInput.val(),
              getPreviewArea: () => components.previewArea,
            });
          } else if (elements.previewForm.is('.preview-user-form')) {
            components.previewForm = elements.previewForm.previewUserForm({
              getObjects: state.model.all,
              getBody: () => components.editor.getCM().getValue(),
              getSubject: () => elements.subjectInput.val(),
              getPreviewArea: () => components.previewArea,
            });
          }
          // 2.2) Create preview area component:
          components.previewArea = elements.previewArea.previewArea({
          });
        },
      });

      state.model.initialize();
    },
  }
}());

$(document).ready(function () {
  /**************************************************************************
   * BINDING METHODS TO DOM EVENTS AND BINDING PLUGINS
   *************************************************************************/
  controller.initialize();
});

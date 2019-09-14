/*
 **************************************************************************
 * HELPERS
 **************************************************************************
 */
// Based on answer on StackOverflow: https://stackoverflow.com/a/7592235
String.prototype.capitalize = function() {
  return this.replace(/(?:^|\s)\S/, function(a) { return a.toUpperCase(); });
};

const prettifyListName = function (name) {
  return name
    .toLowerCase()
    .replace(/_/g, ' ')
    .capitalize();
};


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

/**
 * A jQuery plugin on top of `<input>` element that stores a list of values.
 *
 * It stores data in two ways:
 * - in a list (in memory), and
 * - as a comma-separated string in `<input>` element value.
 *
 * Any change in stored values is reflected into `<input>` value. This controller
 * provides an easy way to manage the list by providing add, remove and get operations.
 *
 * Returns a public API:
 * - `add(item)`: add item to the values list (prefer to use strings!)
 * - `remove(item)`: remove item from the values;
 * - `all()`: get a copy of all stored values;
 * - `has(item)`: check whether the item is already stored;
 * - `elem`: reference to the `<input>`.
 *
 * @param elem: `<input>` element.
 */
const valuesListInput = function (elem) {
  const input = elem;
  const state = {
    values: [],
  };

  //
  // PRIVATE API
  //
  const api = {
    /** Initialize the view by loading values from <input> into memory. */
    initialize: () => {
      const inputValue = input.val().trim();
      state.values = inputValue === '' ? [] : inputValue.split(',');
      state.values = state.values.filter(x => x !== '');
      },

    /** Reflect current stored values into <input> value. */
    updateInputValue: () => {
      input.val(state.values.join(','));
      },

    /** Add an item into the values list. To be consistent, values are casted to strings. */
    add: item => {
      item = String(item);  // we should make sure that we store data in fixed format,
                            // otherwise we may fail when searching for this item later.
      if (state.values.indexOf(item) < 0) {
        state.values.push(item);
        api.updateInputValue();
      }
      },

    /** Delete an item from the values list. */
    remove: item => {
      item = String(item);
      const index = state.values.indexOf(item);
      if (index >= 0) {
        state.values.splice(index, 1);
        api.updateInputValue();
      }
      },
  };

  // We run initialization immediately, but user can also call it later via public API:
  api.initialize();

  //
  // PUBLIC API
  //
  return {
    initialize: api.initialize,
    add: api.add,
    remove: api.remove,
    all: () => state.values.map(x => x),
    elem: input,
  };
};


const getUserDialogHTML = function (user, rawData = undefined) {
  const nameInRus = 'nameInRus' in user ? `<span class="font-weight-light"> [${user.nameInRus}]</span>` : '';
  const rawObject = rawData !== undefined ? rawData : user;
  return `
<img src="${rawObject.avatarURL}" alt="${rawObject.name} profile image" 
     class="rounded-circle mr-3" style="width: 48px; height: 48px;">
<div>
  <p class="dccn-text-0 font-weight-bold">
    ${user.name}${nameInRus} 
    (<a href="${rawObject.url}" class="dccn-text-small font-weight-bold" target="_blank" data-disable-check="1">View...</a>)
  </p>
  <p class="dccn-text-small">${user.country}, ${user.city}, ${user.affiliation}</p>
</div>
<div class="align-self-start ml-auto dccn-text-small">#${user.id}</div>`;
};


const getListDialogHTML = function (object, rawData = undefined) {
  const rawObject = rawData !== undefined ? rawData : object;
  return `
<div class="dccn-text-0">
  <h6 class="font-weight-bold dccn-text-0"> ${object.name} (${rawObject.objects.length} items)
  </h6>
  <p class="m-0 p-0">${object.details}</p>
</div>`;
};


const getSubmissionDialogHTML = function (submission, rawData = undefined) {
  const rawObject = rawData !== undefined ? rawData : submission;
  const authors = rawObject.authors.map(author => author.name).join(', ');
  const title = submission.name ? submission.name : '<span class="text-danger">[No title]</span>';
  return `
<div class="dccn-text-0">
  <p class="font-weight-bold dccn-text-0">
    ${title}
    (<a href="${rawObject.url}" class="dccn-text-small font-weight-bold" target="_blank" data-disable-check="1">View...</a>)
  </p>
  <p class="dccn-text-small m-0 p-0">${authors}</p>
</div>
<div class="align-self-start ml-auto dccn-text-small">#${submission.id}</div>`;
};


const getObjectDialogHTML = (object, rawData = undefined) => {
  const type = object['object_type'];
  if (type === 'user')
    return getUserDialogHTML(object, rawData);
  else if (type === 'submission')
    return getSubmissionDialogHTML(object, rawData);
  else if (type === 'mailing_list')
    return getListDialogHTML(object, rawData);
  throw `unexpected object type "${type}"`;
};


const showObjectsListModal = function ({objects, title, size = 'lg'}) {
  const items = objects.map(object =>
    `<li class="list-group-item d-flex align-items-center">${getObjectDialogHTML(object)}</li>`);
  const content = items.join('');
  const body = `
<div class="list-users-modal-content">
<p class="font-weight-bold"><span class="text-info">${items.length}</span> objects</p>
<ul class="list-group">${content}</ul>
</div>`;
  bootbox.alert({
    size: size,
    title: title,
    message: body,
    buttons: {ok: {label: 'Close', className: 'btn-outline-primary'}}
  });
};


/*
 **************************************************************************
 * MODELS AND DATA MANAGERS
 **************************************************************************
 */
/**
 * Data manager for mailing lists. Provides API for querying mailing list
 * users, caches received data.
 *
 * @param listMailingListsURL: a URL to send HTTP GET request to for reading the mailing lists
 * @param listObjectsURL: a URL to send HTTP GET request to for reading the list of objects (users or submissions)
 * @param onObjectChecked: handler taking `userID` as the input called when a user is checked
 * @param onObjectUnchecked: handler taking `userID` as the input called when a user is unchecked
 * @param onListChecked: handler taking `name` as the input called when a list is checked
 * @param onListUnchecked: handler taking `name` as the input called when a list is unchecked
 * @param onLoaded: optional handler without arguments, called when the model loads all data from the server
 *
 * (!!) IMPORTANT NOTE: for now, we load all mailing lists and users in
 * single AJAX query. In future, we should do something with this...
 *
 * Returns a public API split into `lists` and `users` parts with methods for getting,
 * checking and un-checking items.
 */
const Model = function ({listMailingListsURL, listObjectsURL, onObjectChecked, onObjectUnchecked,
                          onListChecked, onListUnchecked, onLoaded=()=>{}}) {
  const state = {
    lists: {},  // name -> {name, type, details, objects, checked}
    objects: {},  // id -> [submission|user]
    objectType: undefined,
  };

  const api = {
    createUserFromJSON: object => {
      const user = {
        object_type: 'user',
        id: object['id'],
        name: object['name'],
        url: object['url'],
        avatarURL: object['avatar_url'],
        affiliation: object['affiliation'],
        country: object['country'],
        city: object['city'],
        role: object['role'],
        degree: object['degree'],
        checked: false,
        lists: []
      };
      if ('name_rus' in object)
        user.nameInRus = object['name_rus'];
      return user;
      },

    createSubmissionFromJSON: object => {
      return {
        object_type: 'submission',
        id: object['id'],
        name: object['title'],
        url: object['url'],
        authors: object['authors'].map(author => {
          return {id: author['id'], name: author['name']};
        }),
        lists: [],
        checked: false
      }
      },

    createMailingListFromJSON: object => {
      return {
        object_type: 'mailing_list',
        id: object['name'],
        name: prettifyListName(object['name']),
        type: object['type'],
        details: object['details'],
        objects: object['objects'].map(id => id),
        checked: false
      }
      },

    createObjectFromJSON: (type, object) => {
      if (type === 'user')
        return api.createUserFromJSON(object);
      else if (type === 'mailing_list')
        return api.createMailingListFromJSON(object);
      else if (type === 'submission')
        return api.createSubmissionFromJSON(object);
      throw `unrecognized object type "${type}`;
      },

    loadObjects: (url, onFinish = undefined) => {
      $.get(url, data => {
        const type = data['type'];
        let container;
        if (type === 'mailing_list') {
          state.lists = [];
          container = state.lists;
        } else {
          state.objects = [];
          container = state.objects;
          state.objectType = type;
        }
        data['objects'].forEach(receivedObject => {
          const object = api.createObjectFromJSON(type, receivedObject);
          container[object['id']] = object;
        });
        if (onFinish !== undefined)
          onFinish();
      });
    },

    /** Add lists names to `object.lists` fields for each user in the list, for all lists **/
    bindObjectsToLists: () => {
      Object.values(state.objects).forEach(obj => obj.lists = []);
      Object.values(state.lists).forEach(ml => {
        ml.objects.forEach(id => state.objects[id].lists.push(ml.id))
      });
    },

    /** Load lists and users into `state`, bind lists to users */
    load: (success=undefined) => {
      api.loadObjects(listObjectsURL, () => {
        api.loadObjects(listMailingListsURL, () => {
          api.bindObjectsToLists();
          if (success) success();
        });
      });
    },

    _search: (query, objects, fields) => {
      query = query.trim().toLowerCase();
      const words = query === '' ? [] : query.split(/\s+/);
      let _objects = objects;
      const matches = {};
      _objects.forEach(object => matches[object.id] = []); // each match: {fieldName, startIndex, length}
      words.forEach(word => {
        const matchingObjects = [];
        _objects.forEach(object => {
          const found = [];
          fields.forEach(field => {
            if (field in object) {
              const value =  typeof object[field] === 'string' ? object[field] : String(object[field]);
              const index = value.toLowerCase().indexOf(word);
              if (index >= 0) found.push({fieldName: field, startIndex: index, length: word.length});
            }
          });
          if (found.length > 0) {
            matchingObjects.push(object);
            matches[object.id].push(...found);
          }
        });
        _objects = matchingObjects;
      });
      return _objects.map(object => {
        return {object: object, matches: matches[object.id]};
      });
    },

    /** Search for users by a string */
    searchObjects: query => {
      let fields;
      if (state.objectType === 'user')
        fields = ['name', 'nameInRus', 'city', 'affiliation', 'country', 'id'];
      else if (state.objectType === 'submission')
        fields = ['name', 'id'];
      return api._search(query, Object.values(state.objects), fields);
    },

    /** Search mailing lists */
    searchLists: query => {
      const fields = ['name', 'details'];
      return api._search(query, Object.values(state.lists), fields);
    },

    check: (obj, handler) => {
      if (!obj.checked) {
        obj.checked = true;
        if (handler)
          handler(obj.id);
      }
    },

    uncheck: (obj, handler) => {
      if (obj.checked) {
        obj.checked = false;
        if (handler)
          handler(obj.id);
      }
    },

    toggleCheck: (obj, onChecked, onUnchecked) => {
      if (obj.checked) {
        obj.checked = false;
        if (onUnchecked)
          onUnchecked(obj.id);
      } else {
        obj.checked = true;
        if (onChecked)
          onChecked(obj.id);
      }
    },

    isPartOfCheckedList: objectID => state.objects[objectID].lists.some(name => state.lists[name].checked),

    getAllSelectedObjects: () => Object.values(state.objects).filter(o => o.checked || api.isPartOfCheckedList(o.id)),

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
    objects: {
      check: id => api.check(state.objects[id], onObjectChecked),
      uncheck: id => api.uncheck(state.objects[id], onObjectUnchecked),
      toggle: id => api.toggleCheck(state.objects[id], onObjectChecked, onObjectUnchecked),
      get: id => state.objects[id],
      all: () => Object.values(state.objects),
      checked: id => state.objects[id].checked,
      search: query => api.searchObjects(query),
      isPartOfCheckedList: id => api.isPartOfCheckedList(id),
    },
    lists: {
      check: name => api.check(state.lists[name], onListChecked),
      uncheck: name => api.uncheck(state.lists[name], onListUnchecked),
      toggle: name => api.toggleCheck(state.lists[name], onListChecked, onListUnchecked),
      get: name => state.lists[name],
      all: () => Object.values(state.lists),
      checked: name => state.lists[name].checked,
      search: query => api.searchLists(query),
      getObjects: name => name in state.lists ? state.lists[name].objects.map(id => state.objects[id]) : [],
    },
    /** Return a list of all users, either checked directly or included in a checked list */
    allSelectedObjects: () => api.getAllSelectedObjects(),
    getObjectsType: () => state.objectType,
  };
};


/*
 **************************************************************************
 * VIEW CONTROLLERS
 **************************************************************************
 */


/**
 * Compose page 'To' field manager. It renders the list of users and mailing lists in the field and
 * process events regarded to clicking the 'X' buttons for removing mailing lists and users from the
 * 'To' list.
 *
 * @param usersInput: an `<input>` jQuery-element which stores IDs of selected users
 * @param listsInputSelector: an `<input>` jQuery-element which stores names of selected lists
 * @param onUserDeleted: a function taking `id` fired when user is deleted
 * @param onListDeleted: a function taking `id` fired when mailing list is deleted
 * @param getUser: a function for getting user object by his/her ID
 * @param getUsersOf: a function for getting the list (with a given name) users
 * @param getList: a function for getting list object by its name
 *
 * > NOTE: handlers `onUserDeleted` and `onListDeleted` are called ONLY when the deletion is performed
 *         from inside the area, e.g. by clicking 'X' in the label. Otherwise, if deleting item was caused
 *         by public API call of `remove()`, these handlers are NOT called (propagate only events originated
 *         in place)
 *
 *  Public API is grouped into two objects: `users` and `lists`. Each group has the following methods:
 *  - `add(id, name, [url], [items])`
 *  - `remove(id)`
 *  - `all()`
 *  - `has(id)`
 */
$.fn.composeToArea = function ({objectsInput, listsInput, onObjectDeleted, onListDeleted, onObjectAdded, onListAdded,
                                 getList, getObjectsOf, getObject, objectsType}) {

  const getUserItemHTML = user => {
    return`
<div class="compose-to-item" data-type="object" data-id="${user.id}">
<img src="${user.avatarURL}" style="width: 24px; height: 24px;" class="rounded-circle mr-2" alt="user avatar">
<a href="${user.url}" class="dccn-link font-weight-bold">${user.name}</a>
<button class="btn btn-link ml-2 dccn-link" type="button" data-toggle="remove"><i class="fas fa-times"></i></button>
</div>`;
  };

  const getSubmissionItemHTML = submission => {
    return `
<div class="compose-to-item" data-type="object" data-id="${submission.id}">
<i class="fas fa-file mr-2"></i>
<a href="${submission.url}" class="dccn-link font-weight-bold">${submission.name}</a>
<button class="btn btn-link ml-2 dccn-link" type="button" data-toggle="remove"><i class="fas fa-times"></i></button>
</div>`;
  };

  const getListItemHTML = ml => {
    return`
<div class="compose-to-item" data-type="list" data-id="${ml.id}">
<i class="fas fa-list mr-2"></i><a href="#" class="dccn-link font-weight-bold">${ml.name}</a>
<button class="btn btn-link ml-2 dccn-link" type="button" data-toggle="remove"><i class="fas fa-times"></i></button>
</div>`;
  };

  const state = {
    object: {
      items: valuesListInput($(objectsInput)),
      onItemDeleted: onObjectDeleted,
      onItemAdded: onObjectAdded,
      icon: objectsType === 'user' ? 'user' : 'file',
      getHTML: objectsType === 'user' ? getUserItemHTML : getSubmissionItemHTML,
    },
    list: {
      items: valuesListInput($(listsInput)),
      onItemDeleted: onListDeleted,
      onItemAdded: onListAdded,
      icon: 'list',
      getHTML: getListItemHTML,
    },
  };

  const api = {

    /** Build a modal window HTML with a list of users. */
    showListItems: id => showObjectsListModal({
      objects: getObjectsOf(id), title: getList(id).name, size: 'lg'
    }),

    /** Remove an item of a given type ('object' or 'list'). If `internal=true`, call `onItemDeleted(id)` handler. */
    remove: (type, id, internal=false) => {
      const item = this.find(`.compose-to-item[data-type="${type}"][data-id="${id}"]`);
      console.log('remove call: item=', item);
      item.remove();
      console.log('items after removing: ', this.find('.compose-to-item'));
      state[type].items.remove(id);
      console.log('items after calling items.remove(id): ', this.find('.compose-to-item'));
      if (internal)
        state[type].onItemDeleted(id);
      console.log('items after calling onItemDeleted: ', this.find('.compose-to-item'));
      },

    /** Add am object with a given ID. */
    addObject: (id) => {
      this.append(state.object.getHTML(getObject(id)));
      state.object.items.add(id);
      },

    /** Add a list with a given ID (name).`. */
    addList: (id) => {
      this.append(state.list.getHTML(getList(id)));
      state.list.items.add(id);
      },

    /** Initialize the view by binding click event fired at different parts to corresponding actions. */
    initialize: () => {
      // Bind 'click' event to the area and catch it at buttons with [data-toggle="remove"]:
      this.on('click', 'button[data-toggle="remove"]', (event) => {
        const item = $(event.currentTarget).parents('.compose-to-item');
        console.log('going to remove item: ', item);
        api.remove(item.attr('data-type'), item.attr('data-id'), true);
        event.stopPropagation();
        return false;
      });
      // Bind 'click' event to anchors in .compose-to-item's to showing modals with a list of users:
      this.on('click', '.compose-to-item[data-type="list"]', (event) => {
        const item = $(event.currentTarget);
        api.showListItems(item.attr(`data-id`));
        event.stopPropagation();
        return false;
      });
      // Add everything already contained in the lists:
      Object.values(state).forEach(obj => obj.items.all().forEach(obj.onItemAdded));
      },
  };

  return {
    initialize: api.initialize,
    objects: {
      add: (id) => api.addObject(id),
      remove: id => api.remove('object', id),
      all: () => state.object.items.all(),
      has: id => state.object.items.has(id),
    },
    lists: {
      add: name => api.addList(name),
      remove: name => api.remove('list', name),
      all: () => state.list.items.all(),
      has: name => state.lists.items.has(name),
    }
  };
};


/**
 * View controller defined for compose page modal for users selection.
 *
 * @param delay: delay in milliseconds before calling `usersAPI.search()` (by default, 500ms)
 * @param onClick: a handler called when a list is clicked
 * @param isItemDisabled: check that particular item is pre-selected and can not be checked/unchecked
 * @param search: a function for querying list of objects
 * @param getObjects: get all objects
 * @param modalTitle: dialog title
 */
const chooseObjectsDialog = function ({delay = 250, onClick, isItemDisabled = undefined, search,
                                        getObjects, modalTitle}) {
  const DIALOG_DATA_CLASS = 'dialog-data';

  const state = {
    timeoutEventID: undefined,
    dialog: undefined,
    searchResults: [],
  };

  const api = {
    getSearchInput: () => state.dialog.find('input[type="search"]'),
    getResultsArea: () => state.dialog.find(`.${DIALOG_DATA_CLASS}`),

    /** Renders user object (id, name, url, checked) into HTML button */
    getItemHTML: ({object, matches = []}) => {
      const disabled = isItemDisabled !== undefined ? isItemDisabled(object.id) : false;

      /* First we inspect all matches and build an object `markedObject`, in which fields
         are either strings as in original `user` object, or strings with `<mark>...</mark>`
         tags bounding matching substring.
       */
      const markedObject = {_rawObject: object};  // all rendering methods need this to refer to non-marked fields
      Object.keys(object).forEach(fieldName => {
        const fieldValue = String(object[fieldName]);
        // Retrieve matches related to current field only, order them with match start index and
        // build non-overlapping regions:
        const regions = [];
        matches
          .filter(match => match.fieldName === fieldName)
          .sort((x, y) => x.startIndex - y.startIndex)
          .forEach(match => {
            const matchEnd = match.startIndex + match.length;
            const lastRegion = regions.length > 0 ? regions[regions.length - 1] : undefined;
            if (regions.length === 0 || lastRegion.end < match.startIndex) {
              regions.push({start: match.startIndex, end: matchEnd});
            } else if (lastRegion.end < matchEnd) {
              lastRegion.end =  matchEnd;
            }
          });
        // Now we split value into parts corresponding to regions and space between them and mark regions
        // with <mark>...</mark> HTML elements to highlight the matches:
        const parts = [];
        let index = 0;
        regions.forEach(region => {
          parts.push(fieldValue.slice(index, region.start));
          parts.push(`<mark class="p-0 m-0 bg-warning">${fieldValue.slice(region.start, region.end)}</mark>`);
          index = region.end;
        });
        parts.push(fieldValue.slice(index));
        // Finally, we join parts without spaces and put this as the value of marked object field:
        markedObject[fieldName] = parts.join('');
      });

      /* Prepare some optional or logic fields */
      const checked = object.checked || disabled;
      const objectHTML = getObjectDialogHTML(markedObject, object);

      return `
<button class="list-group-item list-group-item-action d-flex align-items-center ${disabled ? 'disabled' : ''}" 
        type="button" data-id="${markedObject._rawObject.id}">
  <i class="far fa-2x mr-3 ${checked ? 'fa-check-square' : 'fa-square'}"></i>
  ${objectHTML}
</button>
`;
      },

    /** Render the found objects list */
    render: () => {
      const value = api.getSearchInput().val().trim();
      const resultsArea = api.getResultsArea();
      let items = [];
      if (state.searchResults.length > 0) {
        items = state.searchResults.map(api.getItemHTML);
      } else if (value === '') {
        items = getObjects().map(object => api.getItemHTML({object: object}));
      }
      if (items.length > 0) {
        resultsArea.html(`<div class="list-group mt-3">${items.join('\n')}</div>`);
      } else {
        resultsArea.html(`<p class="text-center text-info my-3">Nothing found</p>`);
      }
      },

    /** Send search request, store results and render found records */
    search: value => {
      state.searchResults = search(value);
      api.render();
      },

    /** Handle changes in search input */
    handleSearchInputUpdated: function (event) {
      const value = $(event.target).val();
      if (state.timeoutEventID !== undefined)
        clearTimeout(state.timeoutEventID);
      state.timeoutEventID = setTimeout(() => {
        if (state.dialog !== undefined) {
          api.search(value);
        }
        state.timeoutEventID = undefined;
      }, delay);
      },

    show: () => {
      state.dialog = bootbox.alert({
        title: modalTitle,
        message: `
<input type="search" class="form-control form-control-lg" placeholder="Start typing..." value="">
<div class=${DIALOG_DATA_CLASS}></div>`,
        onEscape: true,
        animate: false,
        size: 'xl',
        buttons: {ok: {label: 'Close', className: 'btn-outline-secondary'}},
      });

      // Setup elements and bind handlers to them:
      const input = api.getSearchInput();
      input.on('input', api.handleSearchInputUpdated);
      input.on('propertychange', api.handleSearchInputUpdated);

      const resultsArea = api.getResultsArea();
      resultsArea.on('click', 'button[data-id]', (event) => {
        const disableCheckAttr = $(event.target).attr('data-disable-check');
        if (disableCheckAttr !== '1') {
          onClick($(event.currentTarget).attr('data-id'))
        }
      });

      state.dialog.on('shown.bs.modal', api.render);
      state.dialog.on('hidden.bs.modal', api.hide);

      api.render();
      },

    hide: () => {
      state.dialog = undefined;
      state.searchResults = [];
      if (state.timeoutEventID !== undefined) {
        clearTimeout(state.timeoutEventID);
        state.timeoutEventID = undefined;
      }
      },
  };

  return {
    show: () => { if (state.dialog === undefined) api.show(); },
    hide: () => { if (state.dialog !== undefined) api.hide(); },
    render: () => { if (state.dialog !== undefined) api.render(); },
  }
};


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
    composeToArea: undefined,
    listsDialog: undefined,
    objectsDialog: undefined,
    previewForm: undefined,
    previewArea: undefined,
    editor: undefined,
  };

  const loadElements = () => {
    return {
      composeTo: $('#composeTo'),
      composeToArea: $('#composeToArea'),
      objectsInput: $('#id_objects'),
      listsInput: $('#id_lists'),
      subjectInput: $('#id_subject'),
      previewForm: $('.preview-form'),
      previewArea: $('.preview-message'),
      showRecipientBtn: $('#showRecipientBtn'),
      updatePreviewBtn: $('#updatePreviewBtn'),
      userSearchResults: $('.user-search-results'),
    }
  };

  return {
    initialize: function () {
      // 0) Load all page elements:
      elements = loadElements();

      // 1) Create the editor. It will be used by other components, so we need to instantiate it prior to other parts:
      components.editor = $('.message-editor').messageEditor({
        textarea: $('#id_body')[0],
      });

      // 1) Build the model, and create other components when data is loaded:
      state.model = Model({
        listMailingListsURL: elements.composeTo.attr('data-list-mailing-lists-url'),
        listObjectsURL: elements.composeTo.attr('data-list-objects-url'),
        onObjectChecked: (id) => {
          components.composeToArea.objects.add(id);
          components.objectsDialog.render();
          components.previewForm.update();
        },
        onObjectUnchecked: (id) => {
          components.composeToArea.objects.remove(id);
          components.objectsDialog.render();
          components.previewForm.update();
        },
        onListChecked: (id) => {
          components.composeToArea.lists.add(id);
          components.listsDialog.render();
          components.objectsDialog.render();
          components.previewForm.update();
        },
        onListUnchecked: (id) => {
          components.composeToArea.lists.remove(id);
          components.listsDialog.render();
          components.objectsDialog.render();
          components.previewForm.update();
        },
        onLoaded: () => {
          // 1.1) Create `composeTo` plugin:
          components.composeToArea = elements.composeToArea.composeToArea({
            objectsInput: elements.objectsInput,
            listsInput: elements.listsInput,
            onObjectDeleted: id => state.model.objects.uncheck(id),
            onListDeleted: id => state.model.lists.uncheck(id),
            onObjectAdded: id => state.model.objects.check(id),
            onListAdded: id => state.model.lists.check(id),
            getObject: id => state.model.objects.get(id),
            getObjectsOf: name => state.model.lists.getObjects(name),
            getList: name => state.model.lists.get(name),
            objectsType: state.model.getObjectsType(),
          });
          components.listsDialog = chooseObjectsDialog({
            onClick: state.model.lists.toggle,
            search: state.model.lists.search,
            getObjects: state.model.lists.all,
            modalTitle: 'Search mailing lists',
          });
          // 1.3) Create users list modal plugin:
          components.objectsDialog = chooseObjectsDialog({
            onClick: id => state.model.objects.toggle(id),
            isItemDisabled: id => state.model.objects.isPartOfCheckedList(id),
            search: state.model.objects.search,
            getObjects: () => state.model.objects.all(),
            modalTitle: 'Search items',
          });
          // 1.4) Create preview selector form component:
          if (elements.previewForm.is('.preview-submission-form')) {
            components.previewForm = elements.previewForm.previewSubmissionForm({
              getObjects: state.model.allSelectedObjects,
              getSubmission: state.model.objects.get,
              getBody: () => components.editor.getCM().getValue(),
              getSubject: () => elements.subjectInput.val(),
              getPreviewArea: () => components.previewArea,
            });
          } else if (elements.previewForm.is('.preview-user-form')) {
            components.previewForm = elements.previewForm.previewUserForm({
              getObjects: state.model.allSelectedObjects,
              getBody: () => components.editor.getCM().getValue(),
              getSubject: () => elements.subjectInput.val(),
              getPreviewArea: () => components.previewArea,
            });
          }
          // 1.5) Create preview area component:
          components.previewArea = elements.previewArea.previewArea({
          });

          // 1.5) Initialize the composeToArea component, since it expects other components being ready:
          components.composeToArea.initialize();
        },
      });

      // -----

      // 2) Bind 'Show recipient users' button to displaying a modal with all selected users:
      elements.showRecipientBtn.on('click', (event) => {
        showObjectsListModal({
          objects: state.model.allSelectedObjects(),
          title: 'Recipients',
          size: 'lg',
        });
        event.stopPropagation();
        return false;
      });

      // 3) Bind dialogs to buttons:
      $('.choose-objects-btn').on('click', () => components.objectsDialog.show());
      $('.choose-lists-btn').on('click', () => components.listsDialog.show());

      // 4) Initialize the model:
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

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

const showUserListModal = function ({users, title, size = 'lg'}) {
  const items = users.map(user => `
<li class="list-group-item d-flex align-items-center">
<i class="far fa-2x mr-3 fa-check-square"></i>
<img src="${user.avatarURL}" alt="${user.name} profile image" 
     class="rounded-circle mr-3" style="width: 48px; height: 48px;">
<div>
  <p class="dccn-text-0 font-weight-bold">${user.name}</p>
  <p class="dccn-text-small">${user.country}, ${user.city}, ${user.affiliation}</p>
</div>
<div class="align-self-start ml-auto dccn-text-small">#${user.id}</div>
</li>`);
  const content = items.join('');
  const body = `
<div class="list-users-modal-content">
<p class="font-weight-bold"><span class="text-info">${items.length}</span> users</p>
<ul class="list-group">${content}</ul>
</div>`;
  bootbox.alert({
    size: size,
    title: title,
    message: body,
    buttons: {ok: {label: 'Close', className: 'btn-outline-primary'}}
  });
};

const addClassOnce = function (elem, klass) {
  if (!elem.hasClass(klass)) elem.addClass(klass);
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
 * @param listUsersURL: a URL to send HTTP GET request to for reading the list of users
 * @param onUserChecked: handler taking `userID` as the input called when a user is checked
 * @param onUserUnchecked: handler taking `userID` as the input called when a user is unchecked
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
const Model = function ({listMailingListsURL, listUsersURL, onUserChecked, onUserUnchecked,
                          onListChecked, onListUnchecked, onLoaded=()=>{}}) {
  const state = {
    lists: {},  // name -> {name, type, details, users, [submissions], checked}
    users: {},  // id -> {id, name, [nameInRus], url, checked, lists}
  };

  const api = {
    /** Load all users into `state.users` */
    _loadUsers: (success=undefined) => {
      $.get(listUsersURL, data => {
        data.users.forEach(u => {
          if (!(u.id in state.users)) {
            const aUser = {
              id: u['id'],
              name: u['name'],
              url: u['url'],
              avatarURL: u['avatar_url'],
              affiliation: u['affiliation'],
              country: u['country'],
              city: u['city'],
              role: u['role'],
              degree: u['degree'],
              checked: false,
              lists: []
            };
            if ('name_rus' in u)  aUser.nameInRus = u['name_rus'];
            state.users[u.id] = aUser;
          }
        });
        if (success) success();
      });
    },

    /** Load all mailing lists into `state.lists` */
    _loadLists: (success=undefined) => {
      $.get(listMailingListsURL, {type: 'user'}, data => {
        data.lists.forEach(ml => {
          if (!(ml.name in state.lists)) {
            state.lists[ml.name] = {
              id: ml['name'],
              name: ml['name'],
              type: ml['type'],
              details: ml['details'],
              users: ml['users'].map(userID => userID),
              checked: false,
            };
          }
        });
        if (success) success();
      });
    },

    /** Add lists names to `user.list` fields for each user in the list, for all lists **/
    _bindUsersToLists: () => {
      Object.values(state.users).forEach(u => u.lists = []);
      Object.values(state.lists).forEach(l => l.users.forEach(id => state.users[id].lists.push(l.name)));
    },

    /** Load lists and users into `state`, bind lists to users */
    load: (success=undefined) => {
      api._loadUsers(() => api._loadLists(() => {
        api._bindUsersToLists();
        if (success) success();
      }));
    },

    /** Search for users by a string */
    searchUsers: (query) => {
      query = query.trim().toLowerCase();
      const words = query === '' ? [] : query.split(/\s+/);
      let users = Object.values(state.users);
      const matches = {};
      users.forEach(u => matches[u.id] = []); // each match is an object: {field, startIndex, length}
      words.forEach(word => {
        const matchingUsers = [];
        users.forEach(u => {
          const found = [];
          ['name', 'nameInRus', 'city', 'affiliation', 'country', 'id'].forEach(field => {
            if (field in u) {
              const fieldValue =  typeof u[field] === 'string' ? u[field] : String(u[field]);
              const index = fieldValue.toLowerCase().indexOf(word);
              if (index >= 0) found.push({field: field, startIndex: index, length: word.length});
            }
          });
          if (found.length > 0) {
            matchingUsers.push(u);
            matches[u.id].push(...found);
          }
        });
        users = matchingUsers;
      });
      return users.map(u => {
        return {user: u, matches: matches[u.id]};
      });
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

    isUserPartOfCheckedList: userID => state.users[userID].lists.some(list_name => state.lists[list_name].checked),

    getAllSelectedUsers: () => Object.values(state.users).filter(u => u.checked || api.isUserPartOfCheckedList(u.id)),

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
    users: {
      check: userID => api.check(state.users[userID], onUserChecked),
      uncheck: userID => api.uncheck(state.users[userID], onUserUnchecked),
      toggle: userID => api.toggleCheck(state.users[userID], onUserChecked, onUserUnchecked),
      get: userID => state.users[userID],
      all: () => Object.values(state.users),
      checked: userID => state.users[userID].checked,
      search: query => api.searchUsers(query),
      isPartOfCheckedList: userID => api.isUserPartOfCheckedList(userID),
    },
    lists: {
      check: name => api.check(state.lists[name], onListChecked),
      uncheck: name => api.uncheck(state.lists[name], onListUnchecked),
      toggle: name => api.toggleCheck(state.lists[name], onListChecked, onListUnchecked),
      get: name => state.lists[name],
      all: () => Object.values(state.lists),
      checked: name => state.lists[name].checked,
      getUsers: name => name in state.lists ? state.lists[name].users.map(id => state.users[id]) : [],
    },
    /** Return a list of all users, either checked directly or included in a checked list */
    allSelectedUsers: () => api.getAllSelectedUsers(),
  };
};


/*
 **************************************************************************
 * VIEW CONTROLLERS
 **************************************************************************
 */
/**
 * A view controller on top of `<input>` element that stores a list of values.
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
$.fn.composeToArea = function ({usersInput, listsInput, onUserDeleted, onListDeleted, onUserAdded, onListAdded,
                                 getList, getUsersOf, getUser}) {
  const state = {
    user: {
      items: valuesListInput($(usersInput)),
      onItemDeleted: onUserDeleted,
      onItemAdded: onUserAdded,
      icon: 'user',
    },
    list: {
      items: valuesListInput($(listsInput)),
      onItemDeleted: onListDeleted,
      onItemAdded: onListAdded,
      icon: 'list',
    },
  };

  const api = {
    /** Build HTML for a user item. */
    getUserItemHTML: (user) => {
      return`
<div class="compose-to-item" data-type="user" data-id="${user.id}">
<img src="${user.avatarURL}" style="width: 24px; height: 24px;" class="rounded-circle mr-2" alt="user avatar">
<a href="${user.url}" class="dccn-link font-weight-bold">${user.name}</a>
<button class="btn btn-link ml-2 dccn-link" type="button" data-toggle="remove"><i class="fas fa-times"></i></button>
</div>`;
      },

    /** Build HTML for a user item. */
    getListItemHTML: (ml) => {
      return`
<div class="compose-to-item" data-type="list" data-id="${ml.id}">
<i class="fas fa-list mr-2"></i><a href="#" class="dccn-link font-weight-bold">${prettifyListName(ml.name)}</a>
<button class="btn btn-link ml-2 dccn-link" type="button" data-toggle="remove"><i class="fas fa-times"></i></button>
</div>`;
      },

    /** Build a modal window HTML with a list of users. */
    showListUsersModal: (name) => showUserListModal({
      users: getUsersOf(name), title: prettifyListName(name), size: 'lg'
    }),

    /** Remove an item of a given type ('user' or 'list'). If `internal=true`, call `onItemDeleted(id)` handler. */
    remove: (type, id, internal=false) => {
      const item = this.find(`.compose-to-item[data-type="${type}"][data-id="${id}"]`);
      item.remove();
      state[type].items.remove(id);
      if (internal)
        state[type].onItemDeleted(id);
      },

    /** Add a user with a given ID. */
    addUser: (id) => {
      this.append(api.getUserItemHTML(getUser(id)));
      state.user.items.add(id);
      },

    /** Add a list with a given ID (name).`. */
    addList: (id) => {
      this.append(api.getListItemHTML(getList(id)));
      state.list.items.add(id);
      },

    /** Initialize the view by binding click event fired at different parts to corresponding actions. */
    initialize: () => {
      // Bind 'click' event to the area and catch it at buttons with [data-toggle="remove"]:
      this.on('click', 'button[data-toggle="remove"]', (event) => {
        const item = $(event.currentTarget).parents('.compose-to-item');
        api.remove(item.attr('data-type'), item.attr('data-id'), true);
        event.stopPropagation();
      });
      // Bind 'click' event to anchors in .compose-to-item's to showing modals with a list of users:
      this.on('click', '.compose-to-item[data-type="list"]', (event) => {
        const item = $(event.currentTarget);
        api.showListUsersModal(item.attr(`data-id`));
        event.stopPropagation();
        return false;
      });
      // Add everything already contained in the lists:
      Object.values(state).forEach(obj => obj.items.all().forEach(obj.onItemAdded));
      },
  };

  return {
    initialize: api.initialize,
    users: {
      add: (id) => api.addUser(id),
      remove: id => api.remove('user', id),
      all: () => state.user.items.all(),
      has: id => state.user.items.has(id),
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
 * View controller defined as a JQuery plugin for compose page modal for mailing lists selection.
 *
 * @param getLists - get all mailing lists
 * @param onClick - handle click event, signature: `(userID) => ()`
 *
 * @return this
 */
$.fn.addListModal = function ({getLists, onClick}) {
  if (!this.hasClass('modal')) {
    throw "Must be called on a modal dialog, class 'modal' not found";
  }

  const elements = {
    dialog: this,
    body: this.find('.modal-body')
  };

  const api = {
    getListHTML: mailing_list => {
      const icon = mailing_list.checked ? 'fa-check-square' : 'fa-square';
      return`
<button class="list-group-item list-group-item-action d-flex align-items-center" 
      type="button" data-id="${mailing_list.name}">
<i class="far fa-2x mr-3 ${icon}"></i>
<div class="dccn-text-0">
  <h6 class="font-weight-bold dccn-text-0">
    ${prettifyListName(mailing_list.name)} (${mailing_list.users.length} users)
  </h6>
  <p class="m-0 p-0">${mailing_list.details}</p>
</div>
</button>`;
    },

    render: () => {
      const items = getLists().map(api.getListHTML);
      elements.body.html(`<div class="list-group">${items.join('\n')}</div>`);
      },

    /** Bind `show.bs.modal` event to rendering content and process click events with toggling selection. */
    initialize: () => {
      // Render when the dialog is shown:
      elements.dialog.on('show.bs.modal', api.render);

      // When user clicks a button inside the modal body, we call `onClicked(name)` handler:
      this.on('click', 'button[data-id]', (event) => onClick($(event.currentTarget).attr('data-id')));
    },
  };

  api.initialize();
  return {
    render: api.render,
    modal: this.modal,
  }
};


/**
 * View controller defined for compose page modal for users selection.
 *
 * @param delay: delay in milliseconds before calling `usersAPI.search()` (by default, 500ms)
 * @param onClick: a handler called when a list is clicked
 * @param isPartOfCheckedList: a function for checking whether a user is participated in any list
 * @param searchUsers: a function for querying list of users
 * @param getUsers: get all users
 */
const addUserModal = function ({delay = 250, onClick, isPartOfCheckedList, searchUsers, getUsers}) {
  const state = {
    timeoutEventID: undefined,
    dialog: undefined,
    searchResults: [],
  };

  const api = {
    getSearchInput: () => state.dialog.find('input[type="search"]'),
    getResultsArea: () => state.dialog.find('.user-search-results'),

    /** Renders user object (id, name, url, checked) into HTML button */
    getUserHtml: ({user, matches = []}) => {
      const isPartOfList = isPartOfCheckedList(user.id);
      /* First we inspect all matches and build an object `markedUser`, in which fields
         are either strings as in original `user` object, or strings with `<mark>...</mark>`
         tags bounding matching substring.
       */
      const markedUser = {};
      Object.keys(user).forEach(fieldName => {
        const fieldValue = String(user[fieldName]);
        // Retrieve matches related to current field only, order them with match start index and
        // build non-overlapping regions:
        const regions = [];
        const fieldMatches = matches
          .filter(m => m.field === fieldName)
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
        markedUser[fieldName] = parts.join('');
      });
      /* Prepare some optional or logic fields */
      const checked = user.checked || isPartOfList;
      const nameInRus = 'nameInRus' in markedUser ?
        ` <span class="font-weight-light">(${markedUser.nameInRus})</span>` : '';
      /* Rendering HTML for user item: */
      return `
<button class="list-group-item list-group-item-action d-flex align-items-center ${isPartOfList ? 'disabled' : ''}" 
      type="button" data-id="${user.id}">
<i class="far fa-2x mr-3 ${checked ? 'fa-check-square' : 'fa-square'}"></i>
<img src="${user.avatarURL}" alt="${user.name} profile image" 
     class="rounded-circle mr-3" style="width: 48px; height: 48px;">
<div>
  <p class="dccn-text-0 font-weight-bold">${markedUser.name}${nameInRus}</p>
  <p class="dccn-text-small">${markedUser.country}, ${markedUser.city}, ${markedUser.affiliation}</p>
</div>
<div class="align-self-start ml-auto dccn-text-small">#${markedUser.id}</div>
</button>`;
      },

    /** Render the found users list */
    render: () => {
      const value = api.getSearchInput(state.dialog).val().trim();
      const resultsArea = api.getResultsArea(state.dialog);
      let items = [];
      if (state.searchResults.length > 0) {
        items = state.searchResults.map(api.getUserHtml);
      } else if (value === '') {
        items = getUsers().map(u => api.getUserHtml({user: u}));
      }
      if (items.length > 0) {
        resultsArea.html(`<div class="list-group">${items.join('\n')}</div>`);
      } else {
        resultsArea.html(`<p class="text-center text-info my-3">No users found</p>`);
      }
      },

    /** Send search request, store results and render found records */
    search: value => {
      state.searchResults = searchUsers(value);
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
        title: 'Search users',
        message: `
<input type="search" class="form-control form-control-lg" placeholder="Start typing..." value="">
<div class="user-search-results"></div>`,
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
      resultsArea.on('click', 'button[data-id]', (event) => onClick($(event.currentTarget).attr('data-id')));

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


$.fn.previewSelect = function ({getUsers}) {
  const EMPTY_OPTION_HTML = '<option value="">Select a user</option>';

  const api = {
    getUserHTML: user => `<option value="${user.id}">${user.name} (ID: ${user.id})</option>`,

    render: () => {
      const prevID = this.val();
      const users = getUsers();
      const items = [EMPTY_OPTION_HTML];
      items.push(...users.map(api.getUserHTML));
      this.html(Object.values(items).join(''));
      const nextID = users.filter(u => String(u.id) === prevID).length === 0 ? '' : prevID;
      if (nextID !== prevID) this.change();
      this.val(nextID);
      },

    initialize: () => {
      // Render options:
      api.render();
    },
  };

  api.initialize();
  return {
    render: api.render,
  }
};


$.fn.previewTab = function ({userSelect, subjectInput, codeMirrorEditor}) {
  const elements = {
    previewSubjectField: this.find('.preview-message-subject'),
    previewBodyField: this.find('.preview-message-body')
  };

  const previewUrl = this.attr('data-preview-url');

  const api = {
    initialize: () => {
      },

    render: (subject, body) => {
      elements.subject.text(subject);
      elements.body.html(body);
    },

    update: () => {
      const user = userSelect.val();
      if (user === '') {
        addClassOnce(userSelect, 'is-invalid');
      } else {
        userSelect.removeClass('is-invalid');
        const body = codeMirrorEditor.getValue();
        const subject = subjectInput.val();
        const formData = {'user': user, 'body': body, 'subject': subject};
        $.get(previewUrl, $.param(formData), data => {
          elements.previewSubjectField.text(data.subject);
          elements.previewBodyField.html(data.body);
        });
      }
    },
  };

  return {
    update: () => api.update(),
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
    addListModal: undefined,
    addUserModal: undefined,
    previewSelect: undefined,
    previewTab: undefined,
    editor: undefined,
  };

  const loadElements = () => {
    return {
      composeTo: $('#composeTo'),
      composeToArea: $('#composeToArea'),
      usersInput: $('#id_users'),
      listsInput: $('#id_lists'),
      subjectInput: $('#id_subject'),
      addListModal: $('#addListModal'),
      addUserModal: $('#addUserModal'),
      previewSelect: $('#id_preview_user'),
      showRecipientBtn: $('#showRecipientBtn'),
      updatePreviewBtn: $('#updatePreviewBtn'),
      previewTab: $('#preview-tab'),
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
        listUsersURL: elements.composeTo.attr('data-list-users-url'),
        onUserChecked: (id) => {
          components.composeToArea.users.add(id);
          components.addUserModal.render();
          components.previewSelect.render();
        },
        onUserUnchecked: (id) => {
          components.composeToArea.users.remove(id);
          components.addUserModal.render();
          components.previewSelect.render();
        },
        onListChecked: (id) => {
          components.composeToArea.lists.add(id);
          components.addListModal.render();
          components.addUserModal.render();
          components.previewSelect.render();
        },
        onListUnchecked: (id) => {
          components.composeToArea.lists.remove(id);
          components.addListModal.render();
          components.addUserModal.render();
          components.previewSelect.render();
        },
        onLoaded: () => {
          // 1.1) Create `composeTo` plugin:
          components.composeToArea = elements.composeToArea.composeToArea({
            usersInput: elements.usersInput,
            listsInput: elements.listsInput,
            onUserDeleted: id => state.model.users.uncheck(id),
            onListDeleted: id => state.model.lists.uncheck(id),
            onUserAdded: id => state.model.users.check(id),
            onListAdded: id => state.model.lists.check(id),
            getUser: id => state.model.users.get(id),
            getUsersOf: name => state.model.lists.getUsers(name),
            getList: name => state.model.lists.get(name),
          });
          // 1.2) Create mailing list modal plugin:
          components.addListModal = elements.addListModal.addListModal({
            onClick: name => state.model.lists.toggle(name),
            getLists: () => state.model.lists.all(),
          });
          // 1.3) Create users list modal plugin:
          components.addUserModal = addUserModal({
            // searchResults: elements.userSearchResults,
            onClick: id => state.model.users.toggle(id),
            isPartOfCheckedList: userID => state.model.users.isPartOfCheckedList(userID),
            searchUsers: q => state.model.users.search(q),
            getUsers: () => state.model.users.all(),
          });
          // 1.4) Create preview selector component:
          components.previewSelect = elements.previewSelect.previewSelect({
            getUsers: () => state.model.allSelectedUsers(),
          });
          components.previewTab = elements.previewTab.previewTab({
            userSelect: elements.previewSelect,
            subjectInput: elements.subjectInput,
            codeMirrorEditor: components.editor.getCM(),
          });

          // 1.5) Initialize the composeToArea component, since it expects other components being ready:
          components.composeToArea.initialize();
        },
      });

      // 2) Bind 'Show recipient users' button to displaying a modal with all selected users:
      elements.showRecipientBtn.on('click', (event) => {
        showUserListModal({
          users: state.model.allSelectedUsers(),
          title: 'Recipients',
          size: 'lg'
        });
        event.stopPropagation();
        return false;
      });

      // 3) Bind 'Update' button for updating preview in the preview tab:
      elements.updatePreviewBtn.on('click', () => components.previewTab.update());

      // 4) Bind dialogs to buttons:
      $('#addUserBtn').on('click', () => components.addUserModal.show());

      // 4) Initialize the model:
      state.model.initialize();
    },
  }
}());

$(document).ready(function () {
  /**************************************************************************
   * BINDING METHODS TO DOM EVENTS AND BINDING PLUGINS
   *************************************************************************/
  console.log($('#id_lists'));
  controller.initialize();
});

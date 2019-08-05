/* jshint esversion: 6 */
(function ($) {
  /* dummy data we use in search now */
  const users = {
    users: [{
      id: 20,
      first_name: 'Andrey',
      last_name: 'Sidorov',
      affiliation: 'Moscow State University',
      avatar: '../images/avatar_man.svg'
    }, {
      id: 21,
      first_name: 'Ivan',
      last_name: 'Petrov',
      affiliation: 'Moscow Institute of Physics and Technology',
      avatar: '../images/avatar_man.svg'
    }, {
      id: 22,
      first_name: 'Kate',
      last_name: 'Petrova',
      affiliation: 'Institute of Control Sciences',
      avatar: '../images/avatar_woman.svg'
    }, {
      id: 23,
      first_name: 'Maria',
      last_name: 'Ivanova',
      affiliation: 'Tomsk State University',
      avatar: '../images/avatar_woman.svg'
    }, {
      id: 24,
      first_name: 'Svetlana',
      last_name: 'Sidorova',
      affiliation: 'Ekaterinburg Politechnic Institute',
      avatar: '../images/avatar_woman.svg'
    }]
  };
  /* --- CUT TILL HERE --- */


  /***********************************************************************
   * New author search plugin.
   * 
   ***********************************************************************/
  $.fn.authorSearch = function (options) {
    const content = this.find('.dccn-authors-search-content');
    const showBtn = this.find('.dccn-action-show');
    const hideBtn = this.find('.dccn-action-hide');
    const input = this.find('input[type="search"]');
    const preview = this.find('.dccn-authors-search-preview');
    const placeholder = preview.find('.dccn-placeholder');
    const proposals = preview.find('.dccn-content');
    const form = this.find('.dccn-hidden-form');
    const dataSource = this.attr('data-source');

    const settings = $.extend({
      // 'query()' returns a Promise:
      query: () => {
        const term = input.val().toLowerCase();
        if (dataSource.trim() === "") {
          return new Promise((resolve, reject) => {
            setTimeout(() => { 
              resolve(users.filter(user => {
                return user.first_name.toLowerCase().includes(term) ||
                  user.last_name.toLowerCase().includes(term) ||
                  user.affiliation.toLowerCase().includes(term) ||
                  String(user.id).includes(term);
              })); 
            }, 500);
          });
        }
        return $.get({
          url: dataSource,
          data: $('.dccn-authors-search-form').serialize()
        });
      }
    }, options);
    
    const toggleContent = () => {
      content.toggleClass('active');
      showBtn.toggleClass('d-none');
    };

    const showPreviewScreen = (shownElement) => {
      if (!shownElement.hasClass('active')) {
        proposals.toggleClass('active');
        placeholder.toggleClass('active');  
      }
    };

    const confirmAddAuthor = (user) => {
      const formInput = form.find('input[name="user_pk"]');
      formInput.val(String(user.id));
      form.submit();
    };

    const showAddAuthorDialog = (user) => {
      // Show the modal confirmation dialog:
      Swal.fire({
        showCancelButton: true,
        showCloseButton: true,
        buttonsStyling: false,
        allowOutsideClick: false,
        confirmButtonText: 'Add author',
        customClass: {
          confirmButton: 'btn btn-success btn-lg mr-1',
          cancelButton: 'btn btn-outline-secondary btn-lg'
        },
        animation: false,
        title: 'Confirm add author',
        html: `
<div class="dccn-authors-search-modal-item" data-user--id="${user.id}">
  <img src="${user.avatar}" class="rounded-circle">
  <div>
    <h4 class="dccn-text-large-light">
      ${user.first_name} ${user.last_name}
    </h4>
    <p class="dccn-text-0-light text-muted">
      ${user.affiliation}
    </p>
  </div>
</div>`
      }).then(result => {
        if (result.value) {
          confirmAddAuthor(user);
        }
      });
    };

    const inputUpdateHandler = () => {
      const term = input.val().trim().toLowerCase();
      if (term === '') {
        // Handle term is empty
        showPreviewScreen(placeholder);
      } else {
        // Handle term is not empty

        // Map matching users:
        settings.query().then(users => {
          const formattedUsers = users.users.map(user => {
            // We store additional data in 'data-user--...' attributed to
            // make it easier to grab this data when displaying a modal. 
            return `
  <div class="dccn-authors-search-item" 
      data-user--id="${user.id}" 
      data-user--first-name="${user.first_name}" 
      data-user--last-name="${user.last_name}" 
      data-user--avatar="${user.avatar}" 
      data-user--affiliation="${user.affiliation}">
    <img src="${user.avatar}" class="rounded-circle">
    <div>
      <h4 class="dccn-text-2-light">
        ${user.first_name} ${user.last_name}
      </h4>
      <p class="dccn-text-small text-muted">
        ${user.affiliation}
      </p>
    </div>
  </div>`;
          });
  
          // Check whether found anyone:
          if (formattedUsers.length > 0) {
            showPreviewScreen(proposals);
            // Fill content with data:
            proposals.html(formattedUsers);
  
            // Bind displaying popups to clicking authors:
            proposals.find('.dccn-authors-search-item')
            .click((event) => {
              const item = event.currentTarget;
              showAddAuthorDialog({
                id: $(item).attr('data-user--id'),
                first_name: $(item).attr('data-user--first-name'),
                last_name: $(item).attr('data-user--last-name'),
                affiliation: $(item).attr('data-user--affiliation'),
                avatar: $(item).attr('data-user--avatar'),
              });
            });
  
          } else {
            showPreviewScreen(placeholder);
          }  
        });
      }
    };

    //
    // Binding events
    //
    showBtn.click(toggleContent);
    hideBtn.click(toggleContent);

    input.on('input', inputUpdateHandler);
    input.on('propertychange', inputUpdateHandler);  // for IE8
  };



  // /***********************************************************************
  //  * Authors editor plugin.
  //  * This plugin responds for authors re-ordering and deletion.
  //  ***********************************************************************/
  // $.fn.authorsEditor = function (options) {
  //   const $list = this.find('.dccn-authors-editor-list');
  //   const $input = this.find('.dccn-hidden-form input[type="hidden"]');
  //
  //   $input.change(function () {
  //     console.log($(this).val());  // Here we may send AJAX POST
  //   });
  //
  //   const fillInput = () => {
  //     const $items = this.find('.dccn-authors-editor-author');
  //     const ids = $.map($items, item => { return $(item).attr('data-id'); });
  //     $input.val(String(ids));
  //     $input.trigger('change');
  //   };
  //
  //   $list.sortable({
  //     revert: true,
  //     stop: fillInput,   /* update input only after dragging is over */
  //     create: fillInput  /* we gurantee that input is always filled */
  //   });
  // };

  /***********************************************************************
   * BINDING
   ***********************************************************************/
  // $('.dccn-authors-editor').authorsEditor();
  $('.dccn-authors-search').authorSearch();  
})(jQuery);

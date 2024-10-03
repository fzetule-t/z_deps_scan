function getScoreColor(score) {
   const red = Math.min(255, Math.max(0, Math.round(255 * (score / 10))));
   const green = Math.min(255, Math.max(0, Math.round(255 * ((10 - score) / 10))));
   return `rgb(${red}, ${green}, 0)`;
}


function httpCall(elem, url, redirectUrl, method) {
    $(elem).prop('disabled', true);
    $(elem).removeClass('button-end').addClass('button-start');

    const csrftoken = getCookie('csrftoken');

    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        }
    })
    .then(response => {
        $(elem).prop('disabled', false); // Enable the button
        $(elem).removeClass('button-start').addClass('button-end'); // Change button class

        if (response.ok) {
            window.location.href = redirectUrl; // Redirect on successful response
            return null; // Return null to signal no further processing needed
        } else {
            console.error('There was a problem with the fetch operation:', response.status);
            return response.json(); // Parse JSON response for error handling
        }
    })
    .then(data => {
        if (data != null && data.message) {
            $('#error').text(data.message); // Display error message on #error element
        }
    })
    .catch(error => {
        console.error('Error fetching data:', error); // Log fetch error
        $('#error').text('Error fetching data. Please try again later.'); // Display generic error message
    });
}


function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Extract CSRF token
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function httpDelete(elem, url, redirectUrl) {
    httpCall(elem, url, redirectUrl, 'DELETE');
}

function httpPost(elem, url, redirectUrl) {
    httpCall(elem, url, redirectUrl, 'POST');
}
function httpGet(elem, url, redirectUrl) {
    httpCall(elem, url, redirectUrl, 'GET');
}

function submitSelected(submitUrl, inputName, redirectUrl) {
    const csrfToken = getCookie('csrftoken');
    // Collect selected checkbox values based on inputName
    var selectedValues = $('input[name="' + inputName + '"]:checked').map(function () {
        return $(this).val();
    }).get();

    // Prepare data for POST request
    var postData = {};
    postData[inputName] = selectedValues;

    // Send POST request to submitUrl
    $.ajax({
        url: submitUrl,
        type: 'POST',
        headers: {
            'X-CSRFToken': csrfToken // Include CSRF token in headers
        },
        data: postData,
        traditional: true,
        success: function (response) {
            window.location.href = redirectUrl;
        },
        error: function (xhr, status, error) {
            console.error('POST request error:', error);
            // TODO Handle error'
        }
    });
}

function getColumnsWithHeaderWithClass(idTable, className) {
    var cols = [];

    $('#' + idTable + ' thead th').each(function (index) {
        if ($(this).hasClass(className)) {
            cols.push(index);
        }
    });

    console.log('Columns with class ' + className + ':', cols);
    return cols;
}

function transformToDataTable(idTable) {
    if (! $('#' + idTable).length) {
        return;
    }
    var selectColumns = getColumnsWithHeaderWithClass(idTable, 'selectColumn');
    var noFilterColumns = getColumnsWithHeaderWithClass(idTable, 'noFilter');
    var noSortColumns = getColumnsWithHeaderWithClass(idTable, 'noSort');

    var dataTable = new DataTable('#' + idTable, {
        "order": [],
        fixedHeader: true,
        fixedColumns: true,
        searching: true,
        dom: 'lrtip', // Remove the default search box
        paging: false,
        info: false,
        "asStripeClasses": ['odd', 'even'],
        fixedColumns: true,
        initComplete: function () {
            var api = this.api();
            api
            .columns()
            .every(function (index) {
                let column = this;

                // First column is checkbox selection
                if (index === 0) {
                    // Create checkbox for the first column header
                    let checkAllInput = document.createElement('input');
                    checkAllInput.type = 'checkbox';
                    checkAllInput.addEventListener('change', function () {
                        let isChecked = this.checked;
                        api.column(0, {
                            search: 'applied'
                        }).nodes().to$().find('input[type="checkbox"]').prop('checked', isChecked);
                    });

                    // Replace first column header content with the checkbox
                    api.column(0).header().replaceChildren(checkAllInput);

                    // Event listener for individual checkboxes
                    api.column(0, {
                        search: 'applied'
                    }).nodes().to$().on('change', 'input[type="checkbox"]', function () {
                        let allChecked = true;
                        api.column(0, {
                            search: 'applied'
                        }).nodes().to$().find('input[type="checkbox"]').each(function () {
                            if (!$(this).prop('checked')) {
                                allChecked = false;
                                return false; // Break out of loop
                            }
                        });
                        checkAllInput.checked = allChecked;
                    })
                    return;
                }

                var headerCell = column.header();
                if (!$(headerCell).hasClass('noFilter')) {
                    // For other columns
                    let title = headerCell.textContent;

                    let maxWidth = title.length + 18; //
                    api.column(index).nodes().to$().each(function () {
                        let width = $(this).width(); // Get content width (excluding padding and border)
                        if (width > maxWidth) {
                            maxWidth = width;
                        }
                    });

                    // Create input element
                    let input = document.createElement('input');
                    input.placeholder = title;
                    column.header().replaceChildren(input);
                    // Set initial width based on column width
                    input.style.width = maxWidth + 'px';

                    $(input).bind('keyup', function() {
                        if (column.search() !== this.value) {
                            column.search(input.value).draw();
                        }
                    });
                    //                     }

                    // Prevent sorting when clicking on the input
                    input.addEventListener('click', (e) => {
                        e.stopPropagation();
                    });
                }

            });
        },
        "columnDefs": [{
                targets: 0,
                "width": "30px"
            }, {
                targets: 0,
                orderDataType: "dom-checkbox"
            }, {
                targets: noSortColumns,
                orderable: false
            }, {
                targets: noFilterColumns,
                searchable: false
            }, {
                targets: selectColumns,
                orderDataType: 'dom-select'
            }, {
                targets: selectColumns,
                render: function (data, type, row, meta) {
                    let tempDiv = document.createElement('div');
                    tempDiv.innerHTML = data;
                    let recreatedSelect = tempDiv.querySelector('select');
                    if (recreatedSelect == null) {
                        tempDiv.remove();
                        return data;
                    }
                    let selectedOption = recreatedSelect.options[recreatedSelect.selectedIndex];
                    if(selectedOption == null){
                        return type === 'display' ? data : ''
                    } else {
                        let selectedOptionLabel = selectedOption.textContent;
                        tempDiv.remove();
                        return type === 'display' ? data : selectedOptionLabel;
                    }
                }
            }
        ]
    });
    return dataTable;
}

function activateTab(tabId) {
    function loadTabs() {
        const tabs = JSON.parse(localStorage.getItem('tabs')) || [];
        tabs.forEach(addTabToUI);
    }
    $('#tabList_1 .tab').removeClass('active-tab');
    $('#' + tabId).addClass('active-tab');
}

function addTabTo(tabId, newTabId, newTabText, link) {
    var $existingTab = $('#' + tabId);
    if ($existingTab.length === 0) {
        console.error(`Tab with id ${tabId} not found`);
        return;
    }

    // Create a new <li> element and set its content and id
    var $newTab = $('<li></li>').html('<a href="' + link + '">' + newTabText + '</a>').attr('id', newTabId);

    // Insert the new tab after the existing tab
    $existingTab.after($newTab);

    const tabInfo = {
        id: tabId,
        content: $newTab
    };
    let tabs = JSON.parse(localStorage.getItem('tabs')) || [];
    tabs.push(tabInfo);
    localStorage.setItem('tabs', JSON.stringify(tabs));
}

function datatableRecalculateOddAndEven(tableId) {
    var dataTable = $('#' + tableId).DataTable();
    // Recalculate odd and even classes for visible rows
    var rowNb = 0;
    dataTable.rows({
        search: 'applied'
    }).every(function (rowIdx, tableLoop, rowLoop) {
        var rowNode = this.node();

        // Remove existing odd and even classes
        $(rowNode).removeClass('odd even');

        // Add updated odd and even classes only for visible rows
        if ($(rowNode).is(':visible')) {
            rowNb++;
            $(rowNode).addClass(rowNb % 2 === 0 ? 'even' : 'odd');
        }
    });
}

function initLegend(){
    document.getElementById('toggleButton').addEventListener('click', function() {
        var legend = document.getElementById('legend');
        var ul = legend.querySelector('ul');
        if (ul.style.display === 'none') {
            ul.style.display = 'block';
            this.textContent = '-';
        } else {
            ul.style.display = 'none';
            this.textContent = '+';
        }
    });
}

function applyFilter(idTable) {
       // Get the selected value from the dropdown
       var selectedValue = document.getElementById('filterOptions').value;

       // Initially, hide all rows
       $('#' + idTable + ' tbody tr').hide();
       // Perform actions based on the selected value
       switch (selectedValue) {
           case 'ALL':
           $('#' + idTable + ' tr').show();
           break;
      case 'LATEST':
           $('#' + idTable + ' tr').slice(1).each(function() {
             var hasClass = $(this).find('[class*="version_latest"]').length > 0;
             if (hasClass) {
               $(this).show();
             }
           });
           break;
       case 'HIGHEST':
           $('#' + idTable + ' tr').slice(1).each(function() {
             var hasClass = $(this).find('span[class*="version_highest"]').length > 0;
             if (hasClass) {
               $(this).show();
             }
           });
           break;
       case 'LOWEST':
           $('#' + idTable + ' tr').slice(1).each(function() {
             var hasClass = $(this).find('span[class*="version_lowest"]').length > 0;
             if (hasClass) {
               $(this).show();
             }
           });
           break;
       default:
           // Default case
           alert('Unknown filter option');
       }
        datatableRecalculateOddAndEven('table1');
   }



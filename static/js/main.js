// Main JavaScript for PDF Price Book Parser

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Add loading states to buttons
    addLoadingStates();
    
    // Initialize data tables if present
    initializeDataTables();
    
    // Add smooth scrolling
    addSmoothScrolling();
    
    // Initialize file upload enhancements
    initializeFileUpload();
});

// Add loading states to form submissions
function addLoadingStates() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Processing...';
                submitBtn.disabled = true;
                
                // Re-enable after 10 seconds as fallback
                setTimeout(() => {
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                }, 10000);
            }
        });
    });
}

// Initialize data tables with search and pagination
function initializeDataTables() {
    const tables = document.querySelectorAll('table[data-table="true"]');
    tables.forEach(table => {
        // Add search functionality
        addTableSearch(table);
        
        // Add pagination
        addTablePagination(table);
        
        // Add sorting
        addTableSorting(table);
    });
}

// Add search functionality to tables
function addTableSearch(table) {
    const searchInput = document.createElement('div');
    searchInput.className = 'mb-3';
    searchInput.innerHTML = `
        <div class="input-group">
            <span class="input-group-text">
                <i class="fas fa-search"></i>
            </span>
            <input type="text" class="form-control" placeholder="Search table..." id="search-${table.id}">
        </div>
    `;
    
    table.parentNode.insertBefore(searchInput, table);
    
    const input = searchInput.querySelector('input');
    input.addEventListener('input', function() {
        filterTable(table, this.value);
    });
}

// Filter table rows based on search term
function filterTable(table, searchTerm) {
    const tbody = table.querySelector('tbody');
    if (!tbody) return;
    
    const rows = tbody.querySelectorAll('tr');
    const term = searchTerm.toLowerCase();
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        const shouldShow = text.includes(term);
        row.style.display = shouldShow ? '' : 'none';
    });
}

// Add pagination to tables
function addTablePagination(table) {
    const tbody = table.querySelector('tbody');
    if (!tbody) return;
    
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const rowsPerPage = 10;
    const totalPages = Math.ceil(rows.length / rowsPerPage);
    
    if (totalPages <= 1) return;
    
    // Hide all rows initially
    rows.forEach(row => row.style.display = 'none');
    
    // Show first page
    showPage(rows, 0, rowsPerPage);
    
    // Create pagination controls
    const pagination = createPaginationControls(totalPages, (page) => {
        showPage(rows, page, rowsPerPage);
    });
    
    table.parentNode.appendChild(pagination);
}

// Show specific page of table rows
function showPage(rows, page, rowsPerPage) {
    const start = page * rowsPerPage;
    const end = start + rowsPerPage;
    
    rows.forEach((row, index) => {
        row.style.display = (index >= start && index < end) ? '' : 'none';
    });
}

// Create pagination controls
function createPaginationControls(totalPages, onPageChange) {
    const nav = document.createElement('nav');
    nav.setAttribute('aria-label', 'Table pagination');
    
    const ul = document.createElement('ul');
    ul.className = 'pagination justify-content-center';
    
    for (let i = 0; i < totalPages; i++) {
        const li = document.createElement('li');
        li.className = `page-item ${i === 0 ? 'active' : ''}`;
        
        const a = document.createElement('a');
        a.className = 'page-link';
        a.href = '#';
        a.textContent = i + 1;
        a.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Update active state
            ul.querySelectorAll('.page-item').forEach(item => item.classList.remove('active'));
            li.classList.add('active');
            
            onPageChange(i);
        });
        
        li.appendChild(a);
        ul.appendChild(li);
    }
    
    nav.appendChild(ul);
    return nav;
}

// Add sorting to table headers
function addTableSorting(table) {
    const headers = table.querySelectorAll('th[data-sortable="true"]');
    
    headers.forEach(header => {
        header.style.cursor = 'pointer';
        header.innerHTML += ' <i class="fas fa-sort text-muted"></i>';
        
        header.addEventListener('click', function() {
            const column = Array.from(header.parentNode.children).indexOf(header);
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            
            // Toggle sort direction
            const isAscending = !header.classList.contains('sort-asc');
            
            // Remove sort classes from all headers
            headers.forEach(h => {
                h.classList.remove('sort-asc', 'sort-desc');
                h.querySelector('i').className = 'fas fa-sort text-muted';
            });
            
            // Add sort class to current header
            header.classList.add(isAscending ? 'sort-asc' : 'sort-desc');
            header.querySelector('i').className = `fas fa-sort-${isAscending ? 'up' : 'down'} text-primary`;
            
            // Sort rows
            rows.sort((a, b) => {
                const aText = a.children[column].textContent.trim();
                const bText = b.children[column].textContent.trim();
                
                // Try to parse as numbers
                const aNum = parseFloat(aText.replace(/[^0-9.-]/g, ''));
                const bNum = parseFloat(bText.replace(/[^0-9.-]/g, ''));
                
                if (!isNaN(aNum) && !isNaN(bNum)) {
                    return isAscending ? aNum - bNum : bNum - aNum;
                } else {
                    return isAscending ? aText.localeCompare(bText) : bText.localeCompare(aText);
                }
            });
            
            // Reorder rows in DOM
            rows.forEach(row => tbody.appendChild(row));
        });
    });
}

// Add smooth scrolling to anchor links
function addSmoothScrolling() {
    const links = document.querySelectorAll('a[href^="#"]');
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href').substring(1);
            const target = document.getElementById(targetId);
            
            if (target) {
                e.preventDefault();
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Initialize file upload enhancements
function initializeFileUpload() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
        // Add drag and drop functionality
        const form = input.closest('form');
        if (form) {
            addDragAndDrop(form, input);
        }
        
        // Add file preview
        input.addEventListener('change', function() {
            showFilePreview(this);
        });
    });
}

// Add drag and drop functionality
function addDragAndDrop(form, fileInput) {
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        form.addEventListener(eventName, preventDefaults, false);
    });
    
    ['dragenter', 'dragover'].forEach(eventName => {
        form.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        form.addEventListener(eventName, unhighlight, false);
    });
    
    form.addEventListener('drop', handleDrop, false);
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    function highlight(e) {
        form.classList.add('drag-over');
    }
    
    function unhighlight(e) {
        form.classList.remove('drag-over');
    }
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            fileInput.files = files;
            showFilePreview(fileInput);
        }
    }
}

// Show file preview
function showFilePreview(fileInput) {
    const file = fileInput.files[0];
    if (!file) return;
    
    // Remove existing preview
    const existingPreview = fileInput.parentNode.querySelector('.file-preview');
    if (existingPreview) {
        existingPreview.remove();
    }
    
    // Create preview
    const preview = document.createElement('div');
    preview.className = 'file-preview mt-2 p-3 bg-light rounded';
    preview.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-file-pdf fa-2x text-danger me-3"></i>
            <div>
                <h6 class="mb-1">${file.name}</h6>
                <small class="text-muted">${formatFileSize(file.size)}</small>
            </div>
        </div>
    `;
    
    fileInput.parentNode.appendChild(preview);
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Utility function to show notifications
function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.top = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.zIndex = '9999';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Utility function to confirm actions
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Utility function to format numbers
function formatNumber(num, decimals = 2) {
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(num);
}

// Utility function to format currency
function formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

// Export functions for global use
window.PDFParser = {
    showNotification,
    confirmAction,
    formatNumber,
    formatCurrency,
    filterTable,
    showPage
};

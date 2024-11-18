// 期間入力の切り替え処理
document.addEventListener('DOMContentLoaded', function() {
    const periodTypeSelect = document.getElementById('period_type');
    if (periodTypeSelect) {
        periodTypeSelect.addEventListener('change', function() {
            const singleDateGroup = document.getElementById('single_date_group');
            const dateRangeGroup = document.getElementById('date_range_group');
            
            if (this.value === 'single') {
                singleDateGroup.style.display = 'block';
                dateRangeGroup.style.display = 'none';
                document.getElementById('learning_date').required = true;
                document.getElementById('start_date').required = false;
                document.getElementById('end_date').required = false;
            } else {
                singleDateGroup.style.display = 'none';
                dateRangeGroup.style.display = 'block';
                document.getElementById('learning_date').required = false;
                document.getElementById('start_date').required = true;
                document.getElementById('end_date').required = true;
            }
        });

        // 初期表示時の設定
        periodTypeSelect.dispatchEvent(new Event('change'));
    }
});

// 添付ファイル削除の処理
document.addEventListener('DOMContentLoaded', function() {
    const deleteButtons = document.querySelectorAll('.delete-attachment');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            if (confirm('添付ファイルを削除してもよろしいですか？')) {
                const attachmentId = this.dataset.id;
                const recordId = this.dataset.recordId;
                fetch(`/record/${recordId}/delete_attachment/${attachmentId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        this.closest('p').remove();
                    } else {
                        alert('ファイルの削除に失敗しました');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('エラーが発生しました');
                });
            }
        });
    });
});

// フォームの自動保存
let autoSaveTimeout;
document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form[data-autosave]');
    if (form) {
        const formInputs = form.querySelectorAll('input, textarea, select');
        formInputs.forEach(input => {
            input.addEventListener('input', function() {
                clearTimeout(autoSaveTimeout);
                autoSaveTimeout = setTimeout(function() {
                    const formData = new FormData(form);
                    localStorage.setItem('autosave_' + form.dataset.autosave, JSON.stringify(Object.fromEntries(formData)));
                }, 1000);
            });
        });

        // 保存データの復元
        const savedData = localStorage.getItem('autosave_' + form.dataset.autosave);
        if (savedData) {
            const data = JSON.parse(savedData);
            for (let key in data) {
                const input = form.querySelector(`[name="${key}"]`);
                if (input) {
                    input.value = data[key];
                }
            }
        }
    }
});

// フィルター値の保持
document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    
    const category = urlParams.get('category');
    if (category) {
        document.getElementById('category_filter').value = category;
    }
    
    const dateFrom = urlParams.get('date_from');
    if (dateFrom) {
        document.getElementById('date_from').value = dateFrom;
    }
    
    const dateTo = urlParams.get('date_to');
    if (dateTo) {
        document.getElementById('date_to').value = dateTo;
    }
});
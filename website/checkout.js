document.getElementById('submit').addEventListener('click', submitForm);

async function submitForm(event) {
    event.preventDefault();  // Ngăn form gửi yêu cầu mặc định
    
    // Gửi yêu cầu POST đến server
    const response = await fetch('/place-order', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({})  // Thêm dữ liệu nếu cần
    });

    // Nhận dữ liệu trả về từ server
    const payment = await response.json();

    if (payment && payment.checkoutUrl) {
        // Kiểm tra trước khi mở URL thanh toán
        const paymentUrl = payment.checkoutUrl;
        console.log('Payment URL:', paymentUrl);  // Kiểm tra trong console
        window.open(paymentUrl, '_blank');
    } else {
        console.error('Không có URL thanh toán');
    }
}

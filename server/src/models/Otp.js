import mongoose from 'mongoose'

const otpSchema = new mongoose.Schema({
	email: { type: String, required: true, index: true },
	code: { type: String, required: true },
	createdAt: { type: Date, default: Date.now, expires: 600 } // 10 minutes
})

export default mongoose.model('Otp', otpSchema)
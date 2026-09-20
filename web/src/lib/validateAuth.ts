const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
export const MIN_PASSWORD_LENGTH = 6
export const MIN_FULL_NAME_LENGTH = 2

export const validateEmail = (email: string): string | undefined => {
  if (!email.trim()) return 'Email is required'
  if (!EMAIL_PATTERN.test(email.trim())) return 'Please enter a valid email address'
  return undefined
}

export const validatePassword = (password: string): string | undefined => {
  if (!password) return 'Password is required'
  if (password.length < MIN_PASSWORD_LENGTH) {
    return 'Password must be at least 6 characters'
  }
  return undefined
}

export const validateConfirmPassword = (
  password: string,
  confirmPassword: string,
): string | undefined => {
  if (!confirmPassword) return 'Please confirm your password'
  if (password !== confirmPassword) return 'Passwords do not match'
  return undefined
}

export const validateFullName = (fullName: string): string | undefined => {
  if (!fullName.trim()) return 'Full name is required'
  if (fullName.trim().length < MIN_FULL_NAME_LENGTH) {
    return 'Full name must be at least 2 characters'
  }
  return undefined
}

export type LoginFields = {
  email: string
  password: string
  confirmPassword: string
  fullName: string
}

export const validateLoginFields = (
  fields: LoginFields,
  isSignUp: boolean,
): Partial<LoginFields> => {
  const errors: Partial<LoginFields> = {}
  const emailError = validateEmail(fields.email)
  if (emailError) errors.email = emailError
  const passwordError = validatePassword(fields.password)
  if (passwordError) errors.password = passwordError
  if (isSignUp) {
    const nameError = validateFullName(fields.fullName)
    if (nameError) errors.fullName = nameError
    const confirmError = validateConfirmPassword(fields.password, fields.confirmPassword)
    if (confirmError) errors.confirmPassword = confirmError
  }
  return errors
}

import { validateLoginFields, validatePassword } from './validateAuth'

describe('validateAuth', () => {
  it('requires 6 character passwords', () => {
    expect(validatePassword('short')).toBe('Password must be at least 6 characters')
    expect(validatePassword('123456')).toBeUndefined()
  })

  it('requires name and confirm on sign up', () => {
    const errors = validateLoginFields(
      {
        email: 'ada@example.com',
        password: 'secret1',
        confirmPassword: 'other',
        fullName: 'A',
      },
      true,
    )
    expect(errors.fullName).toBeDefined()
    expect(errors.confirmPassword).toBe('Passwords do not match')
  })
})

subroutine test_fortran_aliases()
  implicit none
  double precision :: a(1), b(1), c(1), alpha, beta
  integer, external :: ilaenv
  integer :: block_size

  a = 2.0d0
  b = 3.0d0
  c = 0.0d0
  alpha = 1.0d0
  beta = 0.0d0
  call dgemm('N', 'N', 1, 1, 1, alpha, a, 1, b, 1, beta, c, 1)
  block_size = ilaenv(1, 'DGETRF', ' ', 1, 1, 1, 1)
end subroutine test_fortran_aliases

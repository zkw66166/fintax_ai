import s from './Pagination.module.css'

export default function Pagination({ currentPage, totalPages, onPageChange }) {
  if (totalPages <= 1) return null

  return (
    <div className={s.pagination}>
      <button
        className={s.pageBtn}
        disabled={currentPage === 1}
        onClick={() => onPageChange(currentPage - 1)}
      >
        上一页
      </button>
      <span className={s.pageInfo}>
        {currentPage} / {totalPages}
      </span>
      <button
        className={s.pageBtn}
        disabled={currentPage === totalPages}
        onClick={() => onPageChange(currentPage + 1)}
      >
        下一页
      </button>
    </div>
  )
}

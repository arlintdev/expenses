import { useSearchParams } from 'react-router-dom';
import ExpenseList from '../components/ExpenseList';

function ExpensesRoute({ apiUrl, onDelete }) {
  const [searchParams] = useSearchParams();

  // Read URL params for filters
  const month = searchParams.get('month') || 'all';
  const year = parseInt(searchParams.get('year')) || new Date().getFullYear();
  const tags = searchParams.get('tags')?.split(',').filter(t => t) || [];
  const search = searchParams.get('search') || '';

  return (
    <ExpenseList
      apiUrl={apiUrl}
      onDelete={onDelete}
      initialMonth={month}
      initialYear={year}
      initialTags={tags}
      initialSearch={search}
    />
  );
}

export default ExpensesRoute;

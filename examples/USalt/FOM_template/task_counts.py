from alframework.tools.tools import parsl_task_queue

def get_task_results(self):
  results = []
  failed = 0
  for task in list(self.task_list):
    status = task.task_status()
    if status == 'exec_done':
      results.append(task.result())
    elif status == 'failed':
      failed += 1
    else:
      continue
    self.task_list.remove(task)
  self.collected_done = getattr(self, 'collected_done', 0) + len(results)
  self.collected_failed = getattr(self, 'collected_failed', 0) + failed
  return results, failed

def print_status(self):
  done = getattr(self, 'collected_done', 0) + self.get_exec_done_number()
  failed = getattr(self, 'collected_failed', 0) + self.get_failed_number()
  total = getattr(self, 'collected_done', 0) + getattr(self, 'collected_failed', 0) + len(self.task_list)
  print('Total Tasks: {:d}'.format(total))
  print('Finished Tasks: {:d}'.format(done + failed))
  print('Finished Successfully Tasks: {:d}'.format(done))
  print('Finished Failed Tasks: {:d}'.format(failed))

parsl_task_queue.get_task_results = get_task_results
parsl_task_queue.print_status = print_status
